import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class MetadataResponse(BaseModel):
    provider: str = Field("UN Population Division", examples=["UN Population Division"])
    endpoint: str = Field(..., examples=["indicators_collect"])
    execution_time_ms: int | None = Field(None, examples=[1000])
    records: int | None = Field(None, examples=[120])
    stored: bool = Field(True)
    ingestion_run_id: uuid.UUID | None = Field(None)
    undata_request_id: uuid.UUID | None = Field(None)
    status: str = Field("success", examples=["success"])
    collected_at: datetime | None = Field(None)


class ObservationResponse(BaseModel):
    country: str = Field(..., examples=["ES"])
    country_name: str | None = Field(None, examples=["Spain"])
    indicator_code: str = Field(..., examples=["TOTAL_POPULATION"])
    indicator_name: str | None = Field(None, examples=["Total Population"])
    time_period: str = Field(..., examples=["2025"])
    value: Decimal | None = Field(None, examples=[48000000])
    unit: str | None = Field(None, examples=["persons"])
    frequency: str | None = Field(None, examples=["A"])


class StandardResponse(BaseModel):
    request: dict[str, Any] = Field(default_factory=dict)
    metadata: MetadataResponse
    data: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["healthy"])
    service: str = Field(..., examples=["marketmind-united-nations-data"])
    database: str = Field(..., examples=["connected"])


class VersionResponse(BaseModel):
    service: str = Field(..., examples=["marketmind-united-nations-data"])
    version: str = Field(..., examples=["0.2.0"])


class DataflowResponse(BaseModel):
    id: uuid.UUID
    agency_id: str | None = None
    dataflow_id: str
    name: str | None = None
    description: str | None = None
    version: str | None = None
    created_at: datetime


class DatastructureResponse(BaseModel):
    id: uuid.UUID
    dataflow_id: str | None = None
    structure_id: str | None = None
    dimension_id: str | None = None
    dimension_name: str | None = None
    dimension_position: int | None = None
    code_id: str | None = None
    code_name: str | None = None
    created_at: datetime


class IndicatorCatalogResponse(BaseModel):
    id: uuid.UUID
    indicator_code: str
    indicator_name: str
    description: str | None = None
    category: str
    expected_unit: str | None = None
    marketmind_dimension: str | None = None
    un_indicator_id: int | None = None
    un_location_id: int | None = None
    default_variant_id: int
    default_age_id: int
    default_sex_id: int
    default_category_id: int
    is_active: bool
    created_at: datetime


class IngestionRunResponse(BaseModel):
    id: uuid.UUID
    source: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    execution_time_ms: int | None = None
    request_payload: dict[str, Any]
    error_message: str | None = None
    created_at: datetime


class UNDataRequestResponse(BaseModel):
    id: uuid.UUID
    ingestion_run_id: uuid.UUID
    endpoint: str
    url: str
    dataset_id: str | None = None
    dataflow_id: str | None = None
    country: str | None = None
    indicator_code: str | None = None
    start_period: str | None = None
    end_period: str | None = None
    request_method: str
    created_at: datetime
