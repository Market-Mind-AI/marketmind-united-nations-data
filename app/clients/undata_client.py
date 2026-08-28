import random
import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import UNDataClientError, UNDataTimeoutError, UNDataTransientError
from app.core.logging import logger


class UNDataClient:
    def __init__(self) -> None:
        self._base_url = settings.undata_api_base_url
        self._timeout = settings.default_timeout
        self._retries = settings.default_retries
        self._backoff = settings.default_backoff

    def get_indicators(self) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/indicators")

    def get_indicator(self, indicator_id: int) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/indicators/{indicator_id}")

    def get_locations(self) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/locations/tvAlphabetical")

    def get_location(self, location_id: int) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/locations/{location_id}")

    def get_sources(self) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/sources")

    def get_time_dimensions(self) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/dimensions/times?timeType=single")

    def get_data(
        self,
        indicator_id: int,
        location_id: int,
        year: int,
        variant_id: int = 4,
        age_id: int = 188,
        sex_id: int = 3,
        category_id: int = 0,
    ) -> list[dict[str, Any]]:
        url = (
            f"{self._base_url}/data/indicators/{indicator_id}"
            f"/locations/{location_id}/years/{year}"
            f"/vars/{variant_id}/ages/{age_id}/sexes/{sex_id}/cats/{category_id}"
        )
        return self._get(url)

    def get_data_range(
        self,
        indicator_id: int,
        location_id: int,
        start_year: int,
        end_year: int,
        variant_id: int = 4,
        age_id: int = 188,
        sex_id: int = 3,
        category_id: int = 0,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """A série do indicador, ano a ano — TOLERANDO ano que falha.

        A API do portal só devolve um ano por chamada, então uma série de 11
        anos são 11 requisições, e até 27/08/2026 qualquer uma que falhasse
        derrubava a série inteira. O ano que derrubava era quase sempre o
        primeiro do laço, o mais antigo, que é justamente o que menos importa:
        os indicadores do MarketMind leem os 3 últimos anos.

        Medido no incidente de 25/08/2026: 78 coletas encerradas em erro porque
        a requisição de 2016 voltou 503 — e com ela foram 9 dos 24 países de uma
        análise, cada um por causa de um ano que ninguém ia usar.

        A regra agora: um ano que falha é registrado e pulado; só quando NENHUM
        ano vem é que o erro sobe. Assim "a fonte está fora do ar" continua
        sendo um erro (e o Core sabe insistir), enquanto "um ano do meio da
        série não veio" deixa de ser.
        """
        all_data: list[dict[str, Any]] = []
        all_raw: list[dict[str, Any]] = []
        anos_perdidos: list[int] = []
        ultimo_erro: Exception | None = None

        for year in range(start_year, end_year + 1):
            try:
                rows = self.get_data(indicator_id, location_id, year, variant_id, age_id, sex_id, category_id)
            except (UNDataTransientError, UNDataTimeoutError, UNDataClientError) as exc:
                anos_perdidos.append(year)
                ultimo_erro = exc
                continue
            all_raw.extend(rows)
            for row in rows:
                if row.get("value") is not None:
                    all_data.append(row)

        if anos_perdidos and not all_raw:
            # Nenhum ano veio: é a fonte fora do ar, não um buraco na série.
            # Precisa subir para a coleta falhar e o Core saber que vale
            # insistir (a causa é transitória).
            logger.warning(
                f"undata_client | indicador {indicator_id} / local {location_id}: "
                f"nenhum dos {len(anos_perdidos)} anos pedidos foi obtido"
            )
            raise ultimo_erro if ultimo_erro is not None else UNDataClientError("No year could be fetched")
        if anos_perdidos:
            logger.warning(
                f"undata_client | indicador {indicator_id} / local {location_id}: "
                f"anos {anos_perdidos} não vieram; série segue com {len(all_raw)} registro(s)"
            )
        return all_data, all_raw

    def _espera(self, attempt: int) -> float:
        """Backoff EXPONENCIAL com jitter, não linear.

        O backoff linear (2s, 4s, 6s) some contra uma indisponibilidade real:
        em 25/08/2026 o portal ficou 29 minutos fora e as 3 tentativas de cada
        requisição se esgotaram em ~6 segundos, sempre dentro da janela ruim.
        Dobrar dá chance de a janela passar sem multiplicar as chamadas.

        O jitter existe porque as requisições saem em rajada — uma coleta são
        11 anos × N indicadores — e sem ele todas repetem no mesmo instante,
        batendo de novo juntas numa fonte que já está sobrecarregada.
        """
        base = self._backoff * (2 ** (attempt - 1))
        return base * random.uniform(1.0, 1.25)

    def _get(self, url: str) -> list[dict[str, Any]]:
        # Only transient upstream failures (timeouts and HTTP 5xx) are retried
        # with linear backoff. Non-transient errors (4xx, generic HTTP errors)
        # are raised immediately — retrying them cannot help and just delays the
        # failure. Without this, a single UN Data Portal 5xx blip permanently
        # drops an indicator and aborts a downstream MarketMind analysis.
        last_error: Exception | None = None

        for attempt in range(1, self._retries + 1):
            try:
                logger.info(f"undata_client | GET {url} | attempt={attempt}/{self._retries}")
                with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                    response = client.get(url)
                    if response.status_code >= 500:
                        raise UNDataTransientError(f"Server error {response.status_code}: {url}")
                    response.raise_for_status()
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict) and "data" in data:
                        return data["data"]
                    return [data] if data else []
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"undata_client | timeout | attempt={attempt}/{self._retries} | url={url}")
                if attempt < self._retries:
                    time.sleep(self._espera(attempt))
            except UNDataTransientError as e:
                last_error = e
                logger.warning(f"undata_client | transient={e.status_code} | attempt={attempt}/{self._retries}")
                if attempt < self._retries:
                    time.sleep(self._espera(attempt))
            except httpx.HTTPStatusError as e:
                # 4xx: non-retryable client error — fail fast.
                logger.warning(f"undata_client | http_error={e.response.status_code} | url={url}")
                raise UNDataClientError(f"HTTP error {e.response.status_code}: {url}") from e
            except httpx.HTTPError as e:
                # Generic (non-transient) HTTP error — fail fast.
                logger.warning(f"undata_client | error={e} | url={url}")
                raise UNDataClientError(f"HTTP error calling UN Data Portal API: {e}") from e

        if isinstance(last_error, httpx.TimeoutException):
            raise UNDataTimeoutError(f"Timeout after {self._retries} retries: {last_error}") from last_error
        if isinstance(last_error, UNDataTransientError):
            raise last_error
        raise UNDataClientError(f"Failed after {self._retries} retries: {last_error}") from last_error
