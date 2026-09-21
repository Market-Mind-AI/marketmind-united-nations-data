from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.responses import HealthResponse, VersionResponse

router = APIRouter()


@router.get(
    "/healthz",
    summary="Is this process alive",
    description=(
        "Answers immediately, reads nothing and calls nobody. That is the only "
        "question a liveness probe should ask: whether THIS process can still "
        "answer.\n\n"
        "GET /health is a different question and belongs on readiness. It opens "
        "a database connection, so a slow Postgres makes it slow — and a "
        "liveness probe pointed at it restarts the pod, which does nothing "
        "about the database and throws away whatever the process was doing. "
        "Readiness is the right place for that check: it takes the pod out of "
        "the load balancer while it cannot serve, and puts it back when it can."
    ),
)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns application status and database connectivity.",
)
def health_check(session: Session = Depends(get_db)) -> HealthResponse:
    try:
        session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        database=db_status,
    )


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="Service Version",
    description="Returns the current service version.",
)
def version() -> VersionResponse:
    return VersionResponse(
        service=settings.app_name,
        version=settings.app_version,
    )
