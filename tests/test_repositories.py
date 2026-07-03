import uuid
from unittest.mock import MagicMock

from app.db.models.ingestion_run import IngestionRun
from app.repositories.ingestion_run_repository import IngestionRunRepository
from app.utils.time import utc_now


class TestIngestionRunRepository:
    def test_create(self, mock_session: MagicMock) -> None:
        repo = IngestionRunRepository(mock_session)
        run = repo.create(source="united_nations_data", request_payload={"test": True})

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        assert run.source == "united_nations_data"
        assert run.status == "running"
        assert run.request_payload == {"test": True}

    def test_mark_success(self, mock_session: MagicMock) -> None:
        repo = IngestionRunRepository(mock_session)
        run = IngestionRun(
            id=uuid.uuid4(),
            source="united_nations_data",
            status="running",
            started_at=utc_now(),
            request_payload={},
            created_at=utc_now(),
        )
        result = repo.mark_success(run, 500)

        assert result.status == "success"
        assert result.execution_time_ms == 500
        assert result.finished_at is not None

    def test_mark_failed(self, mock_session: MagicMock) -> None:
        repo = IngestionRunRepository(mock_session)
        run = IngestionRun(
            id=uuid.uuid4(),
            source="united_nations_data",
            status="running",
            started_at=utc_now(),
            request_payload={},
            created_at=utc_now(),
        )
        result = repo.mark_failed(run, "test error", 100)

        assert result.status == "failed"
        assert result.error_message == "test error"
        assert result.execution_time_ms == 100
