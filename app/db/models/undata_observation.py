import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UNDataObservation(Base):
    __tablename__ = "undata_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    undata_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("undata_requests.id"), nullable=False
    )
    dataset_id: Mapped[str | None] = mapped_column(String, nullable=True)
    dataflow_id: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str] = mapped_column(String, nullable=False)
    country_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    indicator_code: Mapped[str] = mapped_column(String, nullable=False)
    indicator_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    frequency: Mapped[str | None] = mapped_column(String, nullable=True)
    time_period: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    normalized_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_undata_observations_undata_request_id", "undata_request_id"),
        Index("ix_undata_observations_dataset_id", "dataset_id"),
        Index("ix_undata_observations_dataflow_id", "dataflow_id"),
        Index("ix_undata_observations_country", "country"),
        Index("ix_undata_observations_indicator_code", "indicator_code"),
        Index("ix_undata_observations_time_period", "time_period"),
        Index("ix_undata_observations_series", "country", "indicator_code", "time_period"),
    )
