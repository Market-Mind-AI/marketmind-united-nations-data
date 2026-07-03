import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.undata_datastructure import UNDataDatastructure
from app.utils.time import utc_now


class UNDataDatastructureRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        dataflow_id: str | None = None,
        structure_id: str | None = None,
        dimension_id: str | None = None,
        dimension_name: str | None = None,
        dimension_position: int | None = None,
        code_id: str | None = None,
        code_name: str | None = None,
        undata_request_id: uuid.UUID | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> UNDataDatastructure:
        ds = UNDataDatastructure(
            id=uuid.uuid4(),
            undata_request_id=undata_request_id,
            dataflow_id=dataflow_id,
            structure_id=structure_id,
            dimension_id=dimension_id,
            dimension_name=dimension_name,
            dimension_position=dimension_position,
            code_id=code_id,
            code_name=code_name,
            raw_payload=raw_payload,
            created_at=utc_now(),
        )
        self._session.add(ds)
        self._session.flush()
        return ds

    def bulk_create(
        self,
        dataflow_id: str,
        dimensions: list[dict[str, Any]],
        undata_request_id: uuid.UUID | None = None,
    ) -> list[UNDataDatastructure]:
        records: list[UNDataDatastructure] = []
        now = utc_now()
        for dim in dimensions:
            codes = dim.get("codes", [])
            if codes:
                for code in codes:
                    ds = UNDataDatastructure(
                        id=uuid.uuid4(),
                        undata_request_id=undata_request_id,
                        dataflow_id=dataflow_id,
                        dimension_id=dim.get("dimension_id"),
                        dimension_name=dim.get("dimension_name"),
                        dimension_position=dim.get("dimension_position"),
                        code_id=code.get("code_id"),
                        code_name=code.get("code_name"),
                        created_at=now,
                    )
                    records.append(ds)
            else:
                ds = UNDataDatastructure(
                    id=uuid.uuid4(),
                    undata_request_id=undata_request_id,
                    dataflow_id=dataflow_id,
                    dimension_id=dim.get("dimension_id"),
                    dimension_name=dim.get("dimension_name"),
                    dimension_position=dim.get("dimension_position"),
                    created_at=now,
                )
                records.append(ds)
        self._session.add_all(records)
        self._session.flush()
        return records

    def get_by_dataflow(self, dataflow_id: str) -> list[UNDataDatastructure]:
        result = self._session.execute(
            select(UNDataDatastructure)
            .where(UNDataDatastructure.dataflow_id == dataflow_id)
            .order_by(UNDataDatastructure.dimension_position)
        )
        return list(result.scalars().all())

    def get_all(self) -> list[UNDataDatastructure]:
        result = self._session.execute(
            select(UNDataDatastructure).order_by(UNDataDatastructure.created_at.desc())
        )
        return list(result.scalars().all())
