from datetime import timedelta
from unittest.mock import MagicMock

from app.schemas.requests import RefreshStaleRequest
from app.services.undata_service import UNDataService
from app.utils.time import utc_now

_POP = "TOTAL_POPULATION"


def _service(mock_session: MagicMock, *, checks: dict | None = None, setups: dict | None = None) -> UNDataService:
    service = UNDataService(mock_session)
    service._freshness_repo.last_checks = MagicMock(return_value=checks or {})
    service._freshness_repo.observation_facts = MagicMock(return_value={})
    service._ingestion_repo.last_collect_setup_by_country = MagicMock(return_value=setups or {})
    service.collect_indicators = MagicMock()
    return service


def _setup(location_id: str = "724", indicators: list[str] | None = None) -> dict:
    return {"location_id": location_id, "indicator_codes": [_POP] if indicators is None else indicators}


def test_a_stale_country_is_collected_again(mock_session: MagicMock) -> None:
    service = _service(
        mock_session,
        checks={("ES", _POP): utc_now() - timedelta(days=45)},
        setups={"ES": _setup()},
    )

    response = service.refresh_stale(RefreshStaleRequest())

    assert response.data["refreshed"] == 1
    service.collect_indicators.assert_called_once()


def test_a_fresh_country_is_left_alone(mock_session: MagicMock) -> None:
    service = _service(
        mock_session,
        checks={("ES", _POP): utc_now() - timedelta(days=2)},
        setups={"ES": _setup()},
    )

    response = service.refresh_stale(RefreshStaleRequest())

    assert response.data["stale_countries"] == 0
    service.collect_indicators.assert_not_called()


def test_the_location_id_comes_from_the_stored_setup(mock_session: MagicMock) -> None:
    """It cannot be derived from the country code, which is exactly why the
    refresh replays instead of composing a request."""
    service = _service(
        mock_session,
        checks={("FR", _POP): utc_now() - timedelta(days=45)},
        setups={"FR": _setup(location_id="250")},
    )

    service.refresh_stale(RefreshStaleRequest())

    assert service.collect_indicators.call_args.args[0].location_id == 250


def test_the_window_moves_to_now(mock_session: MagicMock) -> None:
    service = _service(
        mock_session,
        checks={("ES", _POP): utc_now() - timedelta(days=45)},
        setups={"ES": _setup()},
    )

    service.refresh_stale(RefreshStaleRequest(years_back=5))

    sent = service.collect_indicators.call_args.args[0]
    assert sent.end_year == utc_now().year
    assert sent.start_year == utc_now().year - 4


def test_a_country_never_collected_is_skipped_not_invented(mock_session: MagicMock) -> None:
    service = _service(mock_session, checks={("PE", _POP): utc_now() - timedelta(days=45)}, setups={})

    response = service.refresh_stale(RefreshStaleRequest())

    assert response.data["skipped"] == 1
    service.collect_indicators.assert_not_called()


def test_a_setup_without_a_location_id_is_skipped(mock_session: MagicMock) -> None:
    service = _service(
        mock_session,
        checks={("ES", _POP): utc_now() - timedelta(days=45)},
        setups={"ES": _setup(location_id="")},
    )

    response = service.refresh_stale(RefreshStaleRequest())

    assert response.data["skipped"] == 1
    service.collect_indicators.assert_not_called()


def test_the_pass_is_bounded(mock_session: MagicMock) -> None:
    old = utc_now() - timedelta(days=45)
    countries = ["ES", "BR", "US", "DE", "JP"]
    service = _service(
        mock_session,
        checks={(c, _POP): old for c in countries},
        setups={c: _setup() for c in countries},
    )

    response = service.refresh_stale(RefreshStaleRequest(limit=2))

    assert response.data["stale_countries"] == 5
    assert response.data["attempted"] == 2


def test_one_country_failing_does_not_end_the_pass(mock_session: MagicMock) -> None:
    old = utc_now() - timedelta(days=45)
    service = _service(
        mock_session,
        checks={("ES", _POP): old, ("BR", _POP): old},
        setups={"ES": _setup(), "BR": _setup()},
    )
    service.collect_indicators = MagicMock(side_effect=[RuntimeError("upstream down"), None])

    response = service.refresh_stale(RefreshStaleRequest())

    assert response.data["failed"] == 1
    assert response.data["refreshed"] == 1


def test_no_limit_means_every_stale_country(mock_session) -> None:
    """Um teto de 10 contra 24 países não limpava nem o atraso de uma noite:
    sobravam 14, que na noite seguinte disputavam as mesmas 10 vagas com os que
    tinham acabado de vencer. O padrão agora é sem teto."""
    pedido = RefreshStaleRequest()

    assert pedido.limit is None


def test_a_pass_that_left_countries_behind_can_refuse() -> None:
    """O CronJob chama com `curl --fail`, então um 503 sai diferente de zero: o
    Kubernetes retenta e o que não se resolve fica como Job `Failed`. Sem isso,
    `failed` era só um campo dentro de um 200 — uma noite em que TODOS os países
    falharam terminava com o CronJob anotando lastSuccessfulTime."""
    from types import SimpleNamespace

    import pytest
    from fastapi import HTTPException

    from app.api.routes.undata import _refuse_if_incomplete

    resposta = SimpleNamespace(data=SimpleNamespace(failed=3))

    with pytest.raises(HTTPException) as erro:
        _refuse_if_incomplete(resposta, RefreshStaleRequest(fail_if_incomplete=True))
    assert erro.value.status_code == 503

    # Sem pedir, a chamada manual continua recebendo o relatório parcial.
    _refuse_if_incomplete(resposta, RefreshStaleRequest())


def test_a_complete_pass_never_refuses() -> None:
    from types import SimpleNamespace

    from app.api.routes.undata import _refuse_if_incomplete

    completa = SimpleNamespace(data=SimpleNamespace(failed=0))
    _refuse_if_incomplete(completa, RefreshStaleRequest(fail_if_incomplete=True))
