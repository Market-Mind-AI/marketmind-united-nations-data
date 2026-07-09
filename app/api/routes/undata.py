from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

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
