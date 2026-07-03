import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.undata_dataflow import UNDataDataflow
from app.utils.time import utc_now


class UNDataDataflowRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        dataflow_id: str,
        agency_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        version: str | None = None,
        undata_request_id: uuid.UUID | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> UNDataDataflow:
        df = UNDataDataflow(
            id=uuid.uuid4(),
            undata_request_id=undata_request_id,
            agency_id=agency_id,
            dataflow_id=dataflow_id,
            name=name,
            description=description,
            version=version,
            raw_payload=raw_payload,
            created_at=utc_now(),
        )
        self._session.add(df)
        self._session.flush()
        return df

    def get_all(self) -> list[UNDataDataflow]:
        result = self._session.execute(select(UNDataDataflow).order_by(UNDataDataflow.created_at.desc()))
        return list(result.scalars().all())
