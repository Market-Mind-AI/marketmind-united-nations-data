"""When the UN portal is down, the collection says so -- it is not a
configuration error."""

from unittest.mock import MagicMock

import pytest

from app.core.exceptions import (
    IndicatorNotConfiguredError,
    UNDataClientError,
    UNDataTimeoutError,
    UNDataTransientError,
)
from app.schemas.requests import CollectIndicatorsRequest
from app.services.undata_service import UNDataService


def _service(failure: Exception, codes: int = 2) -> tuple[UNDataService, CollectIndicatorsRequest]:
    service = UNDataService(MagicMock())
    indicator = MagicMock(un_indicator_id=49)
    service._indicator_repo = MagicMock(get_by_code=MagicMock(return_value=indicator))
    service._ingestion_repo = MagicMock()
    service._request_repo = MagicMock()
    service._raw_response_repo = MagicMock()
    service._observation_repo = MagicMock()
    service._client = MagicMock(get_data_range=MagicMock(side_effect=failure))
    request = CollectIndicatorsRequest(
        country="GB",
        location_id=826,
        start_year=2016,
        end_year=2026,
        indicator_codes=["TOTAL_POPULATION", "MEDIAN_AGE"][:codes],
    )
    return service, request


@pytest.mark.parametrize("failure", [UNDataTransientError("502"), UNDataTimeoutError("timeout")])
def test_the_portal_being_down_is_a_503(failure: Exception) -> None:
    """22/10/2026: the portal answered 502 for 50 minutes and every collection
    came back as a 422 'indicator not configured'."""
    service, request = _service(failure)

    with pytest.raises(UNDataTransientError) as raised:
        service.collect_indicators(request)

    assert raised.value.status_code == 503
    assert "unavailable" in raised.value.message


def test_a_client_error_is_still_a_422() -> None:
    service, request = _service(UNDataClientError("400 bad request"))

    with pytest.raises(IndicatorNotConfiguredError):
        service.collect_indicators(request)


def test_an_unconfigured_indicator_is_still_a_422() -> None:
    service, request = _service(UNDataTransientError("502"))
    service._indicator_repo.get_by_code.return_value = None

    with pytest.raises(IndicatorNotConfiguredError):
        service.collect_indicators(request)
