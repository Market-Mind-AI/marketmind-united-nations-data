from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.undata_observation import UNDataObservation
from app.db.models.undata_request import UNDataRequest

Pair = tuple[str, str]


@dataclass(frozen=True)
class ObservationFacts:
    last_observation_at: datetime
    latest_period: str | None
    observation_count: int


class FreshnessRepository:
    """Answers "when did we last look at this?", per country and indicator.

    Two separate questions, deliberately not one join. A CHECK is a request we
    made (undata_requests), and it happened whether or not UN Data had anything
    to give back. An OBSERVATION is data that landed. Reading freshness off
    observations alone would report a country the source genuinely has no data
    for as "never checked" forever, and it would be re-fetched every day.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def last_checks(
        self, *, countries: list[str] | None = None, indicators: list[str] | None = None
    ) -> dict[Pair, datetime]:
        stmt = (
            select(UNDataRequest.country, UNDataRequest.indicator_code, func.max(UNDataRequest.created_at))
            .where(UNDataRequest.country.is_not(None))
            .where(UNDataRequest.indicator_code.is_not(None))
            .group_by(UNDataRequest.country, UNDataRequest.indicator_code)
        )
        if countries:
            stmt = stmt.where(UNDataRequest.country.in_(countries))
        if indicators:
            stmt = stmt.where(UNDataRequest.indicator_code.in_(indicators))

        return {(row[0], row[1]): row[2] for row in self._session.execute(stmt).all()}

    def observation_facts(
        self, *, countries: list[str] | None = None, indicators: list[str] | None = None
    ) -> dict[Pair, ObservationFacts]:
        stmt = select(
            UNDataObservation.country,
            UNDataObservation.indicator_code,
            func.max(UNDataObservation.created_at),
            func.max(UNDataObservation.time_period),
            func.count(),
        ).group_by(UNDataObservation.country, UNDataObservation.indicator_code)
        if countries:
            stmt = stmt.where(UNDataObservation.country.in_(countries))
        if indicators:
            stmt = stmt.where(UNDataObservation.indicator_code.in_(indicators))

        return {
            (row[0], row[1]): ObservationFacts(
                last_observation_at=row[2], latest_period=row[3], observation_count=row[4]
            )
            for row in self._session.execute(stmt).all()
        }
