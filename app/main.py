from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.undata import router as undata_router
from app.core.config import settings
from app.core.logging import logger
from app.db.session import SessionLocal
from app.services.undata_service import UNDataService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    # Idempotent (upserts by indicator_code) — safe to run on every startup,
    # not just after a fresh volume. Never blocks startup: a transient
    # failure here just means POST /indicators/catalog/seed still works
    # manually, same as before this existed.
    try:
        session = SessionLocal()
        try:
            UNDataService(session).seed_catalog()
        finally:
            session.close()
        logger.info("Indicator catalog seeded on startup")
    except Exception as e:
        logger.error(f"Startup catalog seed failed (non-fatal): {e}")
    yield
    logger.info(f"Shutting down {settings.app_name}")


app = FastAPI(
    title="MarketMind United Nations Data API",
    description=(
        "Microservice for consuming, normalizing and persisting United Nations Population Data "
        "via the UN Population Data Portal REST API (population.un.org). "
        "This service does NOT calculate MOS, Entropy Weight, TOPSIS, or use LLMs. "
        "It collects demographic, social and population data, normalizes responses, "
        "and stores everything in PostgreSQL for auditing, traceability and future analysis."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(health_router, tags=["Health"])
app.include_router(undata_router, tags=["UNdata"])
