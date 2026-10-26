"""Uma linha por período na leitura, e a coleta nova substituindo a velha na escrita."""

from unittest.mock import MagicMock

from sqlalchemy.dialects import postgresql

from app.repositories.undata_observation_repository import UNDataObservationRepository


def _sql(statement: object) -> str:
    return str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))  # type: ignore[attr-defined]


def test_the_series_holds_one_value_per_period_from_the_latest_collection(mock_session: MagicMock) -> None:
    """Depois de uma segunda coleta, `limit=3` devolvia [2025, 2025, 2024] e a
    média de três anos do Core saía errada."""
    mock_session.execute.return_value.scalars.return_value.all.return_value = []

    UNDataObservationRepository(mock_session).series(country="ES", indicator_code="TOTAL_POPULATION", limit=3)

    sql = _sql(mock_session.execute.call_args.args[0])
    assert "DISTINCT ON (undata_observations.time_period)" in sql
    assert (
        "ORDER BY undata_observations.time_period DESC, undata_observations.created_at DESC, "
        "undata_observations.value DESC" in sql
    )


def test_a_new_collection_replaces_the_periods_it_brings(mock_session: MagicMock) -> None:
    observations = [
        {"country": "ES", "indicator_code": "TOTAL_POPULATION", "time_period": "2025", "value": 1},
        {"country": "ES", "indicator_code": "TOTAL_POPULATION", "time_period": "2024", "value": 2},
    ]

    UNDataObservationRepository(mock_session).replace_periods(undata_request_id="req", observations=observations)  # type: ignore[arg-type]

    sql = _sql(mock_session.execute.call_args.args[0])
    assert sql.startswith("DELETE FROM undata_observations")
    assert "undata_observations.time_period IN ('2024', '2025')" in sql
