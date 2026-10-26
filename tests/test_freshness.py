from datetime import timedelta
from unittest.mock import MagicMock

from app.repositories.freshness_repository import ObservationFacts
from app.services.undata_service import UNDataService
from app.utils.time import utc_now

_POP = "TOTAL_POPULATION"
_URB = "URBAN_POPULATION"


def _service(mock_session: MagicMock, *, checks: dict | None = None, observed: dict | None = None) -> UNDataService:
    service = UNDataService(mock_session)
    service._freshness_repo.last_checks = MagicMock(return_value=checks or {})
    service._freshness_repo.observation_facts = MagicMock(return_value=observed or {})
    return service


def test_a_recent_check_is_not_stale(mock_session: MagicMock) -> None:
    yesterday = utc_now() - timedelta(days=1)
    service = _service(mock_session, checks={("ESP", _POP): yesterday})

    items = service.get_freshness(countries=["ESP"], indicators=[_POP]).data["items"]

    assert [(i["country"], i["stale"]) for i in items] == [("ESP", False)]
    assert items[0]["last_checked_at"] == yesterday


def test_an_old_check_is_stale(mock_session: MagicMock) -> None:
    service = _service(mock_session, checks={("ESP", _POP): utc_now() - timedelta(days=91)})

    items = service.get_freshness(countries=["ESP"], indicators=[_POP]).data["items"]

    assert items[0]["stale"] is True


def test_yearly_data_is_not_stale_just_because_the_period_is_old(mock_session: MagicMock) -> None:
    """UN Data publishes yearly. A 2024 population figure IS the current one,
    and a rule written against the period would re-fetch it every day of 2026."""
    service = _service(
        mock_session,
        checks={("ESP", _POP): utc_now() - timedelta(days=2)},
        observed={
            ("ESP", _POP): ObservationFacts(
                last_observation_at=utc_now() - timedelta(days=2), latest_period="2024", observation_count=75
            )
        },
    )

    items = service.get_freshness(countries=["ESP"], indicators=[_POP]).data["items"]

    assert items[0]["latest_period"] == "2024"
    assert items[0]["stale"] is False


def test_a_pair_never_checked_is_reported_rather_than_omitted(mock_session: MagicMock) -> None:
    """The 29-minute UN Data outage in August left nine of twenty-four countries
    without data. A caller has to be able to tell "never tried" from "nothing
    to report", and an empty list says neither."""
    service = _service(mock_session)

    items = service.get_freshness(countries=["PER"], indicators=[_POP]).data["items"]

    assert len(items) == 1
    assert items[0]["last_checked_at"] is None
    assert items[0]["stale"] is True


def test_a_check_that_returned_nothing_still_counts_as_checked(mock_session: MagicMock) -> None:
    service = _service(mock_session, checks={("PER", _POP): utc_now() - timedelta(days=3)})

    item = service.get_freshness(countries=["PER"], indicators=[_POP]).data["items"][0]

    assert item["observation_count"] == 0
    assert item["last_observation_at"] is None
    assert item["stale"] is False


def test_only_stale_filters_out_what_is_fresh(mock_session: MagicMock) -> None:
    service = _service(
        mock_session,
        checks={("ESP", _POP): utc_now() - timedelta(days=1), ("ESP", _URB): utc_now() - timedelta(days=91)},
    )

    items = service.get_freshness(countries=["ESP"], indicators=[_POP, _URB], only_stale=True).data["items"]

    assert [i["indicator_code"] for i in items] == [_URB]


def test_country_codes_are_normalised(mock_session: MagicMock) -> None:
    service = _service(mock_session, checks={("ESP", _POP): utc_now()})

    item = service.get_freshness(countries=[" esp "], indicators=[_POP]).data["items"][0]

    assert item["country"] == "ESP"
    assert item["stale"] is False


def test_the_threshold_is_configurable(mock_session: MagicMock) -> None:
    service = _service(mock_session, checks={("ESP", _POP): utc_now() - timedelta(days=10)})

    fresh = service.get_freshness(countries=["ESP"], indicators=[_POP], stale_after_days=30)
    stale = service.get_freshness(countries=["ESP"], indicators=[_POP], stale_after_days=7)

    assert fresh.data["items"][0]["stale"] is False
    assert stale.data["items"][0]["stale"] is True
    assert stale.data["stale_after_days"] == 7


def test_the_envelope_reports_what_was_asked(mock_session: MagicMock) -> None:
    service = _service(mock_session, checks={("ESP", _POP): utc_now()})

    response = service.get_freshness(countries=["ESP"], indicators=[_POP])

    assert response.metadata.endpoint == "freshness"
    assert response.metadata.stored is False
    assert response.metadata.records == 1


def test_the_default_window_is_the_cores_ninety_days(mock_session: MagicMock) -> None:
    """Indicador de país sai uma vez por ano; o Core o considera bom por 90 dias
    (`country_indicator_ttl_days`). Com o padrão antigo de 30, quem não passava
    a janela renovava todo mês um número que não tinha mudado."""
    service = _service(mock_session, checks={("ESP", _POP): utc_now() - timedelta(days=60)})

    response = service.get_freshness(countries=["ESP"], indicators=[_POP])

    assert response.data["stale_after_days"] == 90
    assert response.data["items"][0]["stale"] is False
