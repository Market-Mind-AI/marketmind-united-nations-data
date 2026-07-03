import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.raw_api_response import RawApiResponse
from app.utils.time import utc_now


class RawApiResponseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        undata_request_id: uuid.UUID,
        endpoint: str,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any] | None = None,
        response_xml: str | None = None,
        response_text: str | None = None,
    ) -> RawApiResponse:
        raw = RawApiResponse(
            id=uuid.uuid4(),
            undata_request_id=undata_request_id,
            endpoint=endpoint,
            request_payload=request_payload,
            response_payload=response_payload,
            response_xml=response_xml,
            response_text=response_text,
            created_at=utc_now(),
        )
        self._session.add(raw)
        self._session.flush()
        return raw
