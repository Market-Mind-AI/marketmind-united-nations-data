import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UNDataRequest(Base):
    __tablename__ = "undata_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_runs.id"), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_id: Mapped[str | None] = mapped_column(String, nullable=True)
    dataflow_id: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    indicator_code: Mapped[str | None] = mapped_column(String, nullable=True)
    start_period: Mapped[str | None] = mapped_column(String, nullable=True)
    end_period: Mapped[str | None] = mapped_column(String, nullable=True)
    request_method: Mapped[str] = mapped_column(String, nullable=False)
    query_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_undata_requests_ingestion_run_id", "ingestion_run_id"),
        Index("ix_undata_requests_endpoint", "endpoint"),
        Index("ix_undata_requests_dataset_id", "dataset_id"),
        Index("ix_undata_requests_dataflow_id", "dataflow_id"),
        Index("ix_undata_requests_country", "country"),
        Index("ix_undata_requests_indicator_code", "indicator_code"),
    )
