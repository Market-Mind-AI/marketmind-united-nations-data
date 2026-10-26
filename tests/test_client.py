from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.clients.undata_client import UNDataClient
from app.core.exceptions import (
    UNDataClientError,
    UNDataEmptyResponseError,
    UNDataTimeoutError,
    UNDataTransientError,
)


MOCK_INDICATORS = [{"id": 49, "name": "Total population by sex", "shortName": "TPopulation"}]
MOCK_LOCATIONS = [{"id": 724, "name": "Spain", "iso3": "ESP", "iso2": "ES"}]
MOCK_DATA = [
    {
        "locationId": 724,
        "indicatorId": 49,
        "timeLabel": "2020",
        "value": 47679489,
        "sex": "Both sexes",
        "variant": "Medium",
        "ageLabel": "Total",
    }
]


class TestUNDataClient:
    @patch("app.clients.undata_client.httpx.Client")
    def test_get_indicators(self, mock_client_class: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_INDICATORS
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = UNDataClient()
        result = client.get_indicators()
        assert len(result) == 1
        assert result[0]["id"] == 49

    @patch("app.clients.undata_client.httpx.Client")
    def test_get_locations(self, mock_client_class: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_LOCATIONS
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = UNDataClient()
        result = client.get_locations()
        assert len(result) == 1
        assert result[0]["iso2"] == "ES"

    @patch("app.clients.undata_client.httpx.Client")
    def test_get_data(self, mock_client_class: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_DATA
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = UNDataClient()
        result = client.get_data(indicator_id=49, location_id=724, year=2020)
        assert len(result) == 1
        assert result[0]["value"] == 47679489

    @patch("app.clients.undata_client.httpx.Client")
    def test_timeout_raises(self, mock_client_class: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = UNDataClient()
        client._retries = 1
        with pytest.raises(UNDataTimeoutError):
            client.get_indicators()

    @patch("app.clients.undata_client.httpx.Client")
    def test_http_error_raises(self, mock_client_class: MagicMock) -> None:
        # 4xx is a non-retryable client error.
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = UNDataClient()
        with pytest.raises(UNDataClientError):
            client.get_indicators()
        assert mock_client.get.call_count == 1

    @patch("app.clients.undata_client.httpx.Client")
    def test_a_404_is_the_source_saying_it_has_no_data(self, mock_client_class: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        with pytest.raises(UNDataEmptyResponseError):
            UNDataClient().get_indicators()

    @patch("app.clients.undata_client.httpx.Client")
    def test_a_429_is_retried(self, mock_client_class: MagicMock) -> None:
        """Até 26/10/2026 este cliente não repetia 429; agora segue a mesma
        política dos outros coletores (app/utils/retry.py)."""
        limitado = MagicMock(status_code=429, headers={"Retry-After": "0"})
        ok = MagicMock(status_code=200)
        ok.json.return_value = MOCK_INDICATORS
        mock_client = MagicMock()
        mock_client.get.side_effect = [limitado, ok]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        assert UNDataClient().get_indicators() == MOCK_INDICATORS

    @patch("app.clients.undata_client.httpx.Client")
    def test_a_network_error_is_retried(self, mock_client_class: MagicMock) -> None:
        ok = MagicMock(status_code=200)
        ok.json.return_value = MOCK_INDICATORS
        mock_client = MagicMock()
        mock_client.get.side_effect = [httpx.ConnectError("dns"), ok]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        assert UNDataClient().get_indicators() == MOCK_INDICATORS

    @patch("app.clients.undata_client.httpx.Client")
    def test_server_error_raises_transient(self, mock_client_class: MagicMock) -> None:
        # 5xx is a transient upstream failure: raised as the retryable
        # UNDataTransientError (before raise_for_status) and re-raised after
        # retries are exhausted.
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = UNDataClient()
        client._retries = 3
        with pytest.raises(UNDataTransientError):
            client.get_indicators()

        # All attempts were exhausted (retried), and raise_for_status was never
        # reached because the 5xx is intercepted first.
        assert mock_client.get.call_count == 3
        mock_response.raise_for_status.assert_not_called()

    @patch("app.clients.undata_client.httpx.Client")
    def test_get_data_range(self, mock_client_class: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_DATA
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = UNDataClient()
        data, raw = client.get_data_range(indicator_id=49, location_id=724, start_year=2020, end_year=2021)
        assert len(data) == 2
        assert len(raw) == 2


class TestSerieToleraAnoQueFalha:
    """A API do portal devolve UM ano por chamada, então uma série de 11 anos são
    11 requisições. Até 27/08/2026 qualquer uma que falhasse derrubava a série
    inteira — e a que derrubava era quase sempre a primeira do laço, o ano mais
    antigo, justamente o que menos importa: os indicadores do MarketMind leem os
    3 últimos anos.

    Medido no incidente de 25/08/2026: 78 coletas encerradas em erro porque a
    requisição de 2016 voltou 503, e com elas 9 dos 24 países de uma análise
    saíram do ranking por causa de um ano que ninguém ia usar.
    """

    @staticmethod
    def _resposta(status: int = 200) -> MagicMock:
        resposta = MagicMock()
        resposta.json.return_value = MOCK_DATA
        resposta.status_code = status
        resposta.raise_for_status = MagicMock()
        return resposta

    @staticmethod
    def _cliente(mock_client_class: MagicMock, respostas: list[MagicMock]) -> MagicMock:
        mock_client = MagicMock()
        mock_client.get.side_effect = respostas
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client
        return mock_client

    @patch("app.clients.undata_client.time.sleep", MagicMock())
    @patch("app.clients.undata_client.httpx.Client")
    def test_ano_que_falha_e_pulado_e_a_serie_sobrevive(self, mock_client_class: MagicMock) -> None:
        # 2016 falha (503 em todas as tentativas), 2017 e 2018 vêm.
        respostas = [self._resposta(503) for _ in range(3)] + [self._resposta(), self._resposta()]
        self._cliente(mock_client_class, respostas)

        client = UNDataClient()
        client._retries = 3  # a lista de respostas acima conta com 3 tentativas por ano
        data, raw = client.get_data_range(indicator_id=49, location_id=724, start_year=2016, end_year=2018)

        assert len(raw) == 2, "os dois anos que vieram continuam na série"
        assert len(data) == 2

    @patch("app.clients.undata_client.time.sleep", MagicMock())
    @patch("app.clients.undata_client.httpx.Client")
    def test_nenhum_ano_obtido_ainda_e_erro(self, mock_client_class: MagicMock) -> None:
        """ "A fonte está fora do ar" tem que continuar sendo erro: é assim que a
        coleta falha e o Core sabe que a causa é transitória e vale insistir.
        Engolir isso devolveria série vazia como se fosse resposta legítima."""
        self._cliente(mock_client_class, [self._resposta(503) for _ in range(9)])

        client = UNDataClient()
        client._retries = 3  # 3 anos x 3 tentativas = as 9 respostas acima
        with pytest.raises(UNDataTransientError):
            client.get_data_range(indicator_id=49, location_id=724, start_year=2016, end_year=2018)


class TestBackoffExponencial:
    """A espera é a política comum aos quatro coletores (app/utils/retry.py),
    que herdou daqui a progressão exponencial com jitter."""

    def test_dobra_a_cada_tentativa_com_jitter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """O backoff linear (2s, 4s, 6s) some contra indisponibilidade real: em
        25/08/2026 o portal ficou 29 minutos fora e as 3 tentativas de cada
        requisição se esgotavam em ~6 segundos, sempre dentro da janela ruim."""
        from app.core.config import settings
        from app.utils.retry import backoff_seconds

        monkeypatch.setattr(settings, "default_backoff", 2)
        for tentativa, esperado in ((1, 2), (2, 4), (3, 8)):
            espera = backoff_seconds(tentativa)
            assert esperado <= espera <= esperado * 1.25

    def test_jitter_separa_requisicoes_que_sairam_em_rajada(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Uma coleta são 11 anos × N indicadores saindo juntos. Sem jitter,
        todos repetem no mesmo instante e batem de novo juntos numa fonte que já
        está sobrecarregada."""
        from app.core.config import settings
        from app.utils.retry import backoff_seconds

        monkeypatch.setattr(settings, "default_backoff", 2)
        esperas = {backoff_seconds(2) for _ in range(20)}
        assert len(esperas) > 1, "a espera não pode ser idêntica para todos"

    def test_retry_after_e_obedecido_ate_o_teto(self) -> None:
        from app.utils.retry import MAX_BACKOFF_SECONDS, backoff_seconds

        assert backoff_seconds(1, "7") == 7
        assert backoff_seconds(1, "3600") == MAX_BACKOFF_SECONDS
