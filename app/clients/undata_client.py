import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import (
    UNDataClientError,
    UNDataEmptyResponseError,
    UNDataRateLimitError,
    UNDataTimeoutError,
    UNDataTransientError,
)
from app.core.logging import logger
from app.utils.retry import backoff_seconds, is_retryable_status


class UNDataClient:
    def __init__(self) -> None:
        self._base_url = settings.undata_api_base_url
        self._timeout = settings.default_timeout
        self._retries = settings.default_retries

    def get_indicators(self) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/indicators")

    def get_locations(self) -> list[dict[str, Any]]:
        return self._get(f"{self._base_url}/locations/tvAlphabetical")

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
        ano tem resposta é que o erro sobe. Assim "a fonte está fora do ar"
        continua sendo um erro (e o Core sabe insistir), enquanto "um ano do
        meio da série não veio" deixa de ser. Um ano em que a fonte responde
        404 TEVE resposta: ela não tem o dado, e isso não é falha.
        """
        all_data: list[dict[str, Any]] = []
        all_raw: list[dict[str, Any]] = []
        anos_perdidos: list[int] = []
        respondidos = 0
        ultimo_erro: Exception | None = None

        for year in range(start_year, end_year + 1):
            try:
                rows = self.get_data(indicator_id, location_id, year, variant_id, age_id, sex_id, category_id)
            except UNDataEmptyResponseError:
                rows = []
            except (UNDataTransientError, UNDataClientError) as exc:
                anos_perdidos.append(year)
                ultimo_erro = exc
                continue
            respondidos += 1
            all_raw.extend(rows)
            for row in rows:
                if row.get("value") is not None:
                    all_data.append(row)

        if anos_perdidos and not respondidos:
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

    def _get(self, url: str) -> list[dict[str, Any]]:
        """Uma chamada à API, insistindo enquanto a falha for passageira.

        Quando e quanto insistir é a política comum aos quatro coletores, em
        app/utils/retry.py. A base é a que este serviço já tinha desde que o
        portal ficou 29 minutos fora em 25/08/2026 (exponencial com jitter); o
        que mudou é que agora 429 e erro de rede também são repetidos, e o
        Retry-After é obedecido. Esgotadas as tentativas, a falha passageira
        sobe como UNDataTransientError (503). Um 404 é a fonte dizendo que não
        tem o dado e sobe como UNDataEmptyResponseError, sem repetir; os outros
        4xx sobem como UNDataClientError, também sem repetir.
        """
        last_error: UNDataTransientError | None = None
        for attempt in range(1, self._retries + 1):
            retry_after: str | None = None
            logger.info(f"undata_client | GET {url} | attempt={attempt}/{self._retries}")
            try:
                with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                    response = client.get(url)
            except httpx.TimeoutException as e:
                last_error = UNDataTimeoutError(f"Timeout calling UN Data Portal API: {url}: {e}")
            except httpx.HTTPError as e:
                # Rede: DNS, conexão recusada ou derrubada. É a fonte (ou o
                # caminho até ela) fora do ar, e esperar resolve.
                last_error = UNDataTransientError(f"Network error calling UN Data Portal API: {e}")
            else:
                status = response.status_code
                if is_retryable_status(status):
                    retry_after = response.headers.get("Retry-After")
                    if status == 429:
                        last_error = UNDataRateLimitError(f"Rate limited: {url}")
                    else:
                        last_error = UNDataTransientError(f"Server error {status}: {url}")
                elif status == 404:
                    raise UNDataEmptyResponseError(f"No data at {url}")
                elif status >= 400:
                    raise UNDataClientError(f"HTTP error {status}: {url}")
                else:
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict) and "data" in data:
                        return data["data"]
                    return [data] if data else []

            logger.warning(f"undata_client | attempt={attempt}/{self._retries} failed | {last_error}")
            if attempt < self._retries:
                time.sleep(backoff_seconds(attempt, retry_after))

        raise last_error or UNDataTransientError(f"Failed after {self._retries} attempts: {url}")
