import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UNDataIndicatorCatalog(Base):
    __tablename__ = "undata_indicators_catalog"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    indicator_code: Mapped[str] = mapped_column(String, nullable=False)
    indicator_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    expected_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    marketmind_dimension: Mapped[str | None] = mapped_column(String, nullable=True)
    un_indicator_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    un_location_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_variant_id: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    default_age_id: Mapped[int] = mapped_column(Integer, nullable=False, default=188)
    default_sex_id: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    default_category_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_undata_indicators_catalog_indicator_code", "indicator_code"),
        Index("ix_undata_indicators_catalog_category", "category"),
        Index("ix_undata_indicators_catalog_marketmind_dimension", "marketmind_dimension"),
        Index("ix_undata_indicators_catalog_is_active", "is_active"),
        Index("ix_undata_indicators_catalog_un_indicator_id", "un_indicator_id"),
    )
