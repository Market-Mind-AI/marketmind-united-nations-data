import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.undata_indicator_catalog import UNDataIndicatorCatalog
from app.utils.time import utc_now


class UNDataIndicatorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        indicator_code: str,
        indicator_name: str,
        category: str,
        description: str | None = None,
        expected_unit: str | None = None,
        marketmind_dimension: str | None = None,
        un_indicator_id: int | None = None,
        un_location_id: int | None = None,
        default_variant_id: int = 4,
        default_age_id: int = 188,
        default_sex_id: int = 3,
        default_category_id: int = 0,
        is_active: bool = True,
    ) -> UNDataIndicatorCatalog:
        indicator = UNDataIndicatorCatalog(
            id=uuid.uuid4(),
            indicator_code=indicator_code,
            indicator_name=indicator_name,
            description=description,
            category=category,
            expected_unit=expected_unit,
            marketmind_dimension=marketmind_dimension,
            un_indicator_id=un_indicator_id,
            un_location_id=un_location_id,
            default_variant_id=default_variant_id,
            default_age_id=default_age_id,
            default_sex_id=default_sex_id,
            default_category_id=default_category_id,
            is_active=is_active,
            created_at=utc_now(),
        )
        self._session.add(indicator)
        self._session.flush()
        return indicator

    def get_by_code(self, indicator_code: str) -> UNDataIndicatorCatalog | None:
        result = self._session.execute(
            select(UNDataIndicatorCatalog)
            .where(UNDataIndicatorCatalog.indicator_code == indicator_code)
            .where(UNDataIndicatorCatalog.is_active.is_(True))
            .order_by(UNDataIndicatorCatalog.created_at.desc())
        )
        return result.scalars().first()

    def get_all_active(self) -> list[UNDataIndicatorCatalog]:
        result = self._session.execute(
            select(UNDataIndicatorCatalog)
            .where(UNDataIndicatorCatalog.is_active.is_(True))
            .order_by(UNDataIndicatorCatalog.created_at.desc())
        )
        return list(result.scalars().all())

    def get_all(self) -> list[UNDataIndicatorCatalog]:
        result = self._session.execute(
            select(UNDataIndicatorCatalog).order_by(UNDataIndicatorCatalog.created_at.desc())
        )
        return list(result.scalars().all())
