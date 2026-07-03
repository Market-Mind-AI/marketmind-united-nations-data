from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.undata import router as undata_router
from app.core.config import settings
from app.core.logging import logger

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
)

app.include_router(health_router, tags=["Health"])
app.include_router(undata_router, tags=["UNdata"])

logger.info(f"Starting {settings.app_name} v{settings.app_version}")
