import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.undata_observation import UNDataObservation
from app.utils.time import utc_now


class UNDataObservationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def bulk_create(
        self,
        undata_request_id: uuid.UUID,
        observations: list[dict[str, Any]],
        dataset_id: str | None = None,
        dataflow_id: str | None = None,
    ) -> list[UNDataObservation]:
        records: list[UNDataObservation] = []
        now = utc_now()
        for obs in observations:
            value = obs.get("value")
            if value is not None and not isinstance(value, Decimal):
                value = Decimal(str(value))
            record = UNDataObservation(
                id=uuid.uuid4(),
                undata_request_id=undata_request_id,
                dataset_id=dataset_id,
                dataflow_id=dataflow_id,
                country=obs["country"],
                country_name=obs.get("country_name"),
                indicator_code=obs["indicator_code"],
                indicator_name=obs.get("indicator_name"),
                unit=obs.get("unit"),
                frequency=obs.get("frequency"),
                time_period=obs["time_period"],
                value=value,
                attributes=obs.get("attributes"),
                created_at=now,
            )
            records.append(record)
        self._session.add_all(records)
        self._session.flush()
        return records

    def get_by_request_id(self, undata_request_id: uuid.UUID) -> list[UNDataObservation]:
        result = self._session.execute(
            select(UNDataObservation)
            .where(UNDataObservation.undata_request_id == undata_request_id)
            .order_by(UNDataObservation.time_period)
        )
        return list(result.scalars().all())
