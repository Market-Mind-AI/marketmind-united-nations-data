from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.clients.undata_client import UNDataClient
from app.core.exceptions import UNDataClientError, UNDataTimeoutError


MOCK_INDICATORS = [{"id": 49, "name": "Total population by sex", "shortName": "TPopulation"}]
MOCK_LOCATIONS = [{"id": 724, "name": "Spain", "iso3": "ESP", "iso2": "ES"}]
MOCK_DATA = [{"locationId": 724, "indicatorId": 49, "timeLabel": "2020", "value": 47679489, "sex": "Both sexes", "variant": "Medium", "ageLabel": "Total"}]


class TestUNDataClient:
    @patch("app.clients.undata_client.httpx.Client")
    def test_get_indicators(self, mock_client_class: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_INDICATORS
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
        client._backoff = 0
        with pytest.raises(UNDataTimeoutError):
            client.get_indicators()

    @patch("app.clients.undata_client.httpx.Client")
    def test_http_error_raises(self, mock_client_class: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Error", request=MagicMock(), response=mock_response)
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = UNDataClient()
        client._retries = 1
        client._backoff = 0
        with pytest.raises(UNDataClientError):
            client.get_indicators()

    @patch("app.clients.undata_client.httpx.Client")
    def test_get_data_range(self, mock_client_class: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_DATA
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
