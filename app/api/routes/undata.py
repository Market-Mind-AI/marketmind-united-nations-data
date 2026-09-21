from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_undata_service
from app.core.exceptions import (
    IndicatorNotConfiguredError,
    ResourceNotFoundError,
    UNDataBaseException,
)
from app.schemas.requests import (
    CollectIndicatorsRequest,
    RegisterDataflowsRequest,
    RegisterDatastructuresRequest,
    RegisterIndicatorsCatalogRequest,
)
from app.schemas.responses import StandardResponse
from app.services.undata_service import UNDataService

router = APIRouter()


@router.get(
    "/remote/indicators",
    response_model=StandardResponse,
    summary="List Remote UN Indicators",
    description="Proxy to UN Population Data Portal API. Lists all available indicators.",
)
def get_remote_indicators(service: UNDataService = Depends(get_undata_service)) -> StandardResponse:
    try:
        return service.get_remote_indicators()
    except UNDataBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get(
    "/remote/locations",
    response_model=StandardResponse,
    summary="List Remote UN Locations",
    description="Proxy to UN Population Data Portal API. Lists all available locations (countries, regions).",
)
def get_remote_locations(service: UNDataService = Depends(get_undata_service)) -> StandardResponse:
    try:
        return service.get_remote_locations()
    except UNDataBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/dataflows/register",
    response_model=StandardResponse,
    summary="Register Dataflows",
    description="Register UN data sources/dataflows relevant for MarketMind.",
)
def register_dataflows(
    request: RegisterDataflowsRequest, service: UNDataService = Depends(get_undata_service)
) -> StandardResponse:
    return service.register_dataflows(request)


@router.get(
    "/dataflows",
    response_model=StandardResponse,
    summary="List Dataflows",
    description="List all registered dataflows.",
)
def list_dataflows(service: UNDataService = Depends(get_undata_service)) -> StandardResponse:
    return service.list_dataflows()


@router.post(
    "/datastructures/register",
    response_model=StandardResponse,
    summary="Register Datastructures",
    description="Register dimensions and codelists for a dataflow.",
)
def register_datastructures(
    request: RegisterDatastructuresRequest, service: UNDataService = Depends(get_undata_service)
) -> StandardResponse:
    return service.register_datastructures(request)


@router.get(
    "/datastructures",
    response_model=StandardResponse,
    summary="List Datastructures",
    description="List registered datastructures. Optionally filter by dataflow_id.",
)
def list_datastructures(
    dataflow_id: str | None = None, service: UNDataService = Depends(get_undata_service)
) -> StandardResponse:
    return service.list_datastructures(dataflow_id)


@router.post(
    "/indicators/catalog",
    response_model=StandardResponse,
    summary="Register Indicators Catalog",
    description="Create or update the internal catalog of UN indicators. Each indicator must include un_indicator_id (the numeric ID from the UN Population Data Portal API).",
)
def register_indicators_catalog(
    request: RegisterIndicatorsCatalogRequest, service: UNDataService = Depends(get_undata_service)
) -> StandardResponse:
    return service.register_indicators(request)


@router.get(
    "/observations/series",
    response_model=StandardResponse,
    summary="Read one indicator's stored values for one country",
    description=(
        "Returns the values this service has collected, newest period first, "
        "with nulls dropped.\n\n"
        "Rows come back, never a computed figure: an average, a rate or a ratio "
        "is method, it is versioned, and it belongs to whoever owns the method "
        "rather than to this service.\n\n"
        "Omit `limit` to read the whole series. That is a real use rather than "
        "laziness: lining up two indicators year by year needs both in full, "
        "because the years they cover need not match and the overlap is only "
        "knowable after reading both."
    ),
)
def get_series(
    country: str = Query(..., description="Country code as stored, e.g. ES"),
    indicator_code: str = Query(..., description="Indicator code, e.g. TOTAL_POPULATION"),
    limit: int | None = Query(None, ge=1, le=1000, description="Most recent N periods only."),
    service: UNDataService = Depends(get_undata_service),
) -> StandardResponse:
    return service.get_series(country=country, indicator_code=indicator_code, limit=limit)


@router.get(
    "/freshness",
    response_model=StandardResponse,
    summary="What this service holds, and when it last looked",
    description=(
        "Reports, per country and indicator, when this service last ASKED the "
        "UN -- not how recent the returned data is. UN Data publishes yearly, "
        "so a 2024 population figure is the current one, and a staleness rule "
        "written against the datum's own period would re-fetch every indicator "
        "every day forever.\n\n"
        "A pair that was checked and came back empty still reports a "
        "last_checked_at, so a country the source genuinely has no data for is "
        "not mistaken for one that was never tried.\n\n"
        "Naming both country and indicator asks a closed question and gets a "
        "closed answer: every requested pair is returned, including pairs never "
        "fetched (last_checked_at null, stale true)."
    ),
)
def get_freshness(
    country: list[str] | None = Query(None, description="Country codes. Repeat the parameter for several."),
    indicator: list[str] | None = Query(None, description="Indicator codes. Repeat for several."),
    stale_after_days: int = Query(30, ge=1, le=3650, description="A check older than this counts as stale."),
    only_stale: bool = Query(False, description="Return only the pairs that need collecting."),
    service: UNDataService = Depends(get_undata_service),
) -> StandardResponse:
    return service.get_freshness(
        countries=country,
        indicators=indicator,
        stale_after_days=stale_after_days,
        only_stale=only_stale,
    )


@router.get(
    "/indicators/catalog",
    response_model=StandardResponse,
    summary="List Indicators Catalog",
    description="List the internal catalog of registered UN indicators.",
)
def list_indicators_catalog(service: UNDataService = Depends(get_undata_service)) -> StandardResponse:
    return service.list_indicators()


@router.post(
    "/indicators/catalog/seed",
    response_model=StandardResponse,
    summary="Seed indicator catalog",
    description="Seeds the internal indicator catalog with the default MarketMind indicators (idempotent).",
)
def seed_catalog(service: UNDataService = Depends(get_undata_service)) -> StandardResponse:
    return service.seed_catalog()


@router.post(
    "/indicators/collect",
    response_model=StandardResponse,
    summary="Collect Indicators",
    description="Collect indicators from the UN Population Data Portal API for a given country/location and year range. Each indicator must have un_indicator_id configured in the catalog.",
)
def collect_indicators(
    request: CollectIndicatorsRequest, service: UNDataService = Depends(get_undata_service)
) -> StandardResponse:
    try:
        return service.collect_indicators(request)
    except IndicatorNotConfiguredError as e:
        raise HTTPException(status_code=422, detail=e.message) from e
    except UNDataBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get(
    "/requests/{undata_request_id}",
    response_model=StandardResponse,
    summary="Get UNData Request",
    description="Returns a stored request with its associated observations.",
)
def get_request(undata_request_id: UUID, service: UNDataService = Depends(get_undata_service)) -> StandardResponse:
    try:
        return service.get_request(undata_request_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.get(
    "/runs/{ingestion_run_id}",
    response_model=StandardResponse,
    summary="Get Ingestion Run",
    description="Returns status and metadata of a specific ingestion run.",
)
def get_run(ingestion_run_id: UUID, service: UNDataService = Depends(get_undata_service)) -> StandardResponse:
    try:
        return service.get_run(ingestion_run_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
