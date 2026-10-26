"""When the UN portal is down, the collection says so -- it is not a
configuration error."""

from unittest.mock import MagicMock

import pytest

from app.core.exceptions import (
    IndicatorNotConfiguredError,
    UNDataClientError,
    UNDataEmptyResponseError,
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


def test_nothing_collected_for_another_reason_is_a_502() -> None:
    """Também era 422 "indicator not configured", e não é erro de quem pediu:
    a fonte respondeu algo que não serve."""
    service, request = _service(UNDataClientError("400 bad request"))

    with pytest.raises(UNDataClientError) as raised:
        service.collect_indicators(request)

    assert raised.value.status_code == 502


def test_an_unconfigured_indicator_is_refused_before_anything_is_collected() -> None:
    service, request = _service(UNDataTransientError("502"))
    service._indicator_repo.get_by_code.side_effect = [MagicMock(un_indicator_id=49), None]

    with pytest.raises(IndicatorNotConfiguredError) as raised:
        service.collect_indicators(request)

    assert raised.value.status_code == 422
    service._client.get_data_range.assert_not_called()
    service._ingestion_repo.create.assert_not_called()


def test_the_source_having_no_data_is_an_answer_and_a_check() -> None:
    """Um 404 do portal era falha: execução falhada, sem verificação, e o par
    recoletado toda noite. "Não tenho" é resposta definitiva."""
    service, request = _service(UNDataEmptyResponseError("404"), codes=1)

    response = service.collect_indicators(request)

    assert response.metadata.status == "success"
    assert response.data["indicators_failed"] == []
    assert service._request_repo.create.call_args.kwargs["indicator_code"] == "TOTAL_POPULATION"
    service._ingestion_repo.mark_success.assert_called_once()


def test_only_the_indicators_that_got_an_answer_are_checks() -> None:
    """A linha de requisição nascia antes da chamada; agora só nasce depois que
    a fonte respondeu, como nos outros coletores."""
    service, request = _service(UNDataTransientError("502"))
    service._client.get_data_range.side_effect = [([], []), UNDataTransientError("502")]

    response = service.collect_indicators(request)

    assert [c.kwargs["indicator_code"] for c in service._request_repo.create.call_args_list] == ["TOTAL_POPULATION"]
    assert response.data["indicators_failed"] == ["MEDIAN_AGE"]
    assert response.metadata.status == "success"


def test_an_unconfigured_indicator_is_still_a_422() -> None:
    service, request = _service(UNDataTransientError("502"))
    service._indicator_repo.get_by_code.return_value = None

    with pytest.raises(IndicatorNotConfiguredError):
        service.collect_indicators(request)
