import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.ingestion_run import IngestionRun
from app.domain.enums import IngestionStatus
from app.utils.time import utc_now


class IngestionRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, source: str, request_payload: dict[str, Any]) -> IngestionRun:
        now = utc_now()
        run = IngestionRun(
            id=uuid.uuid4(),
            source=source,
            status=IngestionStatus.RUNNING,
            started_at=now,
            request_payload=request_payload,
            created_at=now,
        )
        self._session.add(run)
        self._session.flush()
        return run

    def mark_success(self, run: IngestionRun, execution_time_ms: int) -> IngestionRun:
        run.status = IngestionStatus.SUCCESS
        run.finished_at = utc_now()
        run.execution_time_ms = execution_time_ms
        self._session.flush()
        return run

    def mark_failed(self, run: IngestionRun, error_message: str, execution_time_ms: int) -> IngestionRun:
        run.status = IngestionStatus.FAILED
        run.finished_at = utc_now()
        run.execution_time_ms = execution_time_ms
        run.error_message = error_message
        self._session.flush()
        return run

    def get_by_id(self, run_id: uuid.UUID) -> IngestionRun | None:
        result = self._session.execute(select(IngestionRun).where(IngestionRun.id == run_id))
        return result.scalar_one_or_none()

    def last_collect_setup_by_country(self) -> dict[str, dict[str, Any]]:
        """Per country, the upstream location id and the indicators it was collected with.

        A refresh replays what was asked before rather than composing a new
        request. That matters more here than elsewhere: collecting from the UN
        needs a numeric location id, which is not derivable from the country
        code this service stores. Replaying means the service never has to keep
        that mapping, and whatever a caller once set up keeps working.

        One run is recorded per indicator, so the indicators for a country are
        gathered across its runs rather than read off a single payload.

        PARTIAL counts alongside SUCCESS. A partial run did return data, so its
        setup is known to work, and an incomplete collection is exactly the one
        worth running again. FAILED is excluded: replaying it would repeat the
        failure on a schedule.
        """
        payload = IngestionRun.request_payload
        country = payload["country"].astext
        indicator = payload["indicator_code"].astext
        stmt = (
            select(country, indicator, payload["location_id"].astext, IngestionRun.started_at)
            .where(IngestionRun.status.in_([IngestionStatus.SUCCESS, IngestionStatus.PARTIAL]))
            .where(country.is_not(None))
            .where(indicator.is_not(None))
            .order_by(IngestionRun.started_at.desc())
        )

        setups: dict[str, dict[str, Any]] = {}
        for country_code, indicator_code, location_id, _started_at in self._session.execute(stmt).all():
            setup = setups.setdefault(country_code, {"location_id": location_id, "indicator_codes": []})
            if indicator_code not in setup["indicator_codes"]:
                setup["indicator_codes"].append(indicator_code)
        return setups
