import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UNDataDatastructure(Base):
    __tablename__ = "undata_datastructures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    undata_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("undata_requests.id"), nullable=True
    )
    dataflow_id: Mapped[str | None] = mapped_column(String, nullable=True)
    structure_id: Mapped[str | None] = mapped_column(String, nullable=True)
    dimension_id: Mapped[str | None] = mapped_column(String, nullable=True)
    dimension_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimension_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_id: Mapped[str | None] = mapped_column(String, nullable=True)
    code_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_undata_datastructures_dataflow_id", "dataflow_id"),
        Index("ix_undata_datastructures_structure_id", "structure_id"),
        Index("ix_undata_datastructures_dimension_id", "dimension_id"),
        Index("ix_undata_datastructures_code_id", "code_id"),
    )
