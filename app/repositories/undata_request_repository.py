import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.undata_request import UNDataRequest
from app.utils.time import utc_now


class UNDataRequestRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        ingestion_run_id: uuid.UUID,
        endpoint: str,
        url: str,
        request_method: str,
        dataset_id: str | None = None,
        dataflow_id: str | None = None,
        country: str | None = None,
        indicator_code: str | None = None,
        start_period: str | None = None,
        end_period: str | None = None,
        query_params: dict[str, Any] | None = None,
    ) -> UNDataRequest:
        req = UNDataRequest(
            id=uuid.uuid4(),
            ingestion_run_id=ingestion_run_id,
            endpoint=endpoint,
            url=url,
            dataset_id=dataset_id,
            dataflow_id=dataflow_id,
            country=country,
            indicator_code=indicator_code,
            start_period=start_period,
            end_period=end_period,
            request_method=request_method,
            query_params=query_params,
            created_at=utc_now(),
        )
        self._session.add(req)
        self._session.flush()
        return req

    def get_by_id(self, request_id: uuid.UUID) -> UNDataRequest | None:
        result = self._session.execute(select(UNDataRequest).where(UNDataRequest.id == request_id))
        return result.scalar_one_or_none()
