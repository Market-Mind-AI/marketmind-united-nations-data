from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.undata_service import UNDataService

_POP = "TOTAL_POPULATION"


def _observation(period: str, value: str) -> SimpleNamespace:
    return SimpleNamespace(time_period=period, value=Decimal(value), unit="persons", frequency="A")


def _service(mock_session: MagicMock, rows: list) -> UNDataService:
    service = UNDataService(mock_session)
    service._observation_repo.series = MagicMock(return_value=rows)
    return service


def test_returns_the_points_newest_first(mock_session: MagicMock) -> None:
    service = _service(mock_session, [_observation("2024", "48000000"), _observation("2023", "47800000")])

    points = service.get_series(country="ES", indicator_code=_POP).data["points"]

    assert [(p["time_period"], p["value"]) for p in points] == [
        ("2024", Decimal("48000000")),
        ("2023", Decimal("47800000")),
    ]


def test_omitting_the_limit_asks_for_the_whole_series(mock_session: MagicMock) -> None:
    """Net migration over total population has to be lined up year by year, and
    the overlap between the two is only knowable after reading both in full."""
    service = _service(mock_session, [])

    service.get_series(country="ES", indicator_code=_POP)

    assert service._observation_repo.series.call_args.kwargs["limit"] is None


def test_the_limit_is_passed_through(mock_session: MagicMock) -> None:
    service = _service(mock_session, [])

    service.get_series(country="ES", indicator_code=_POP, limit=3)

    assert service._observation_repo.series.call_args.kwargs["limit"] == 3


def test_a_country_with_nothing_stored_returns_an_empty_series(mock_session: MagicMock) -> None:
    service = _service(mock_session, [])

    response = service.get_series(country="PE", indicator_code=_POP)

    assert response.data["points"] == []
    assert response.data["country"] == "PE"


def test_the_country_code_is_normalised(mock_session: MagicMock) -> None:
    service = _service(mock_session, [])

    response = service.get_series(country=" es ", indicator_code=f" {_POP} ")

    assert response.data["country"] == "ES"
    assert response.data["indicator_code"] == _POP
    assert service._observation_repo.series.call_args.kwargs["country"] == "ES"


def test_the_envelope_reports_a_read_rather_than_a_collection(mock_session: MagicMock) -> None:
    service = _service(mock_session, [_observation("2024", "1")])

    response = service.get_series(country="ES", indicator_code=_POP)

    assert response.metadata.endpoint == "observations_series"
    assert response.metadata.stored is False
    assert response.metadata.records == 1
