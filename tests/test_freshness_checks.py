"""Only a collection that finished counts as having checked the source."""

from unittest.mock import MagicMock

from app.repositories.freshness_repository import CHECKED_STATUSES, FreshnessRepository


def _sql_of_last_checks() -> str:
    session = MagicMock()
    session.execute.return_value.all.return_value = []
    FreshnessRepository(session).last_checks(countries=["ES"], indicators=["TOTAL_POPULATION"])
    stmt = session.execute.call_args.args[0]
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


def test_a_failed_collection_is_not_a_check() -> None:
    """22/10/2026: the UN portal answered 502 for 50 minutes, twenty collections
    failed, and the next pass saw all twenty as fresh. Their last real data was
    a month old."""
    sql = _sql_of_last_checks()

    assert "JOIN ingestion_runs" in sql
    assert "ingestion_runs.status IN ('success', 'partial')" in sql


def test_only_finished_statuses_count() -> None:
    assert CHECKED_STATUSES == ("success", "partial")
