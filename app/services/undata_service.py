import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.clients.undata_client import UNDataClient
from app.core.config import settings
from app.core.exceptions import (
    IndicatorNotConfiguredError,
    ResourceNotFoundError,
    UNDataBaseException,
)
from app.core.logging import logger
from app.domain.enums import IngestionStatus, RequestMethod
from app.repositories.ingestion_run_repository import IngestionRunRepository
from app.repositories.raw_api_response_repository import RawApiResponseRepository
from app.repositories.undata_dataflow_repository import UNDataDataflowRepository
from app.repositories.undata_datastructure_repository import UNDataDatastructureRepository
from app.repositories.undata_indicator_repository import UNDataIndicatorRepository
from app.repositories.undata_observation_repository import UNDataObservationRepository
from app.repositories.undata_request_repository import UNDataRequestRepository
from app.schemas.requests import (
    CollectIndicatorsRequest,
    RegisterDataflowsRequest,
    RegisterDatastructuresRequest,
    RegisterIndicatorsCatalogRequest,
)
from app.schemas.responses import (
    DataflowResponse,
    DatastructureResponse,
    IndicatorCatalogResponse,
    IngestionRunResponse,
    MetadataResponse,
    ObservationResponse,
    StandardResponse,
    UNDataRequestResponse,
)
from app.utils.normalization import normalize_observations
from app.utils.time import elapsed_ms, utc_now


class UNDataService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._client = UNDataClient()
        self._ingestion_repo = IngestionRunRepository(session)
        self._request_repo = UNDataRequestRepository(session)
        self._raw_response_repo = RawApiResponseRepository(session)
        self._dataflow_repo = UNDataDataflowRepository(session)
        self._datastructure_repo = UNDataDatastructureRepository(session)
        self._observation_repo = UNDataObservationRepository(session)
        self._indicator_repo = UNDataIndicatorRepository(session)

    # ── Remote (proxy to UN API) ──

    def get_remote_indicators(self) -> StandardResponse:
        data = self._client.get_indicators()
        return StandardResponse(
            request={},
            metadata=MetadataResponse(endpoint="remote_indicators", records=len(data), status="success"),
            data={"indicators": data},
        )

    def get_remote_locations(self) -> StandardResponse:
        data = self._client.get_locations()
        return StandardResponse(
            request={},
            metadata=MetadataResponse(endpoint="remote_locations", records=len(data), status="success"),
            data={"locations": data},
        )

    # ── Dataflows ──

    def register_dataflows(self, request: RegisterDataflowsRequest) -> StandardResponse:
        created_ids: list[str] = []
        for df_item in request.dataflows:
            df = self._dataflow_repo.create(
                dataflow_id=df_item.dataflow_id,
                agency_id=df_item.agency_id,
                name=df_item.name,
                description=df_item.description,
                version=df_item.version,
            )
            created_ids.append(str(df.id))
        self._session.commit()
        return StandardResponse(
            request=request.model_dump(),
            metadata=MetadataResponse(endpoint="dataflows_register", records=len(created_ids), stored=True, status="success"),
            data={"dataflow_ids": created_ids},
        )

    def list_dataflows(self) -> StandardResponse:
        dataflows = self._dataflow_repo.get_all()
        return StandardResponse(
            request={},
            metadata=MetadataResponse(endpoint="dataflows", records=len(dataflows), status="success"),
            data={"dataflows": [DataflowResponse(id=d.id, agency_id=d.agency_id, dataflow_id=d.dataflow_id, name=d.name, description=d.description, version=d.version, created_at=d.created_at).model_dump() for d in dataflows]},
        )

    # ── Datastructures ──

    def register_datastructures(self, request: RegisterDatastructuresRequest) -> StandardResponse:
        records = self._datastructure_repo.bulk_create(dataflow_id=request.dataflow_id, dimensions=[d.model_dump() for d in request.dimensions])
        self._session.commit()
        return StandardResponse(
            request=request.model_dump(),
            metadata=MetadataResponse(endpoint="datastructures_register", records=len(records), stored=True, status="success"),
            data={"records_created": len(records)},
        )

    def list_datastructures(self, dataflow_id: str | None = None) -> StandardResponse:
        structures = self._datastructure_repo.get_by_dataflow(dataflow_id) if dataflow_id else self._datastructure_repo.get_all()
        return StandardResponse(
            request={"dataflow_id": dataflow_id} if dataflow_id else {},
            metadata=MetadataResponse(endpoint="datastructures", records=len(structures), status="success"),
            data={"datastructures": [DatastructureResponse(id=s.id, dataflow_id=s.dataflow_id, structure_id=s.structure_id, dimension_id=s.dimension_id, dimension_name=s.dimension_name, dimension_position=s.dimension_position, code_id=s.code_id, code_name=s.code_name, created_at=s.created_at).model_dump() for s in structures]},
        )

    # ── Indicators Catalog ──

    def register_indicators(self, request: RegisterIndicatorsCatalogRequest) -> StandardResponse:
        created_ids: list[str] = []
        for item in request.indicators:
            indicator = self._indicator_repo.create(
                indicator_code=item.indicator_code,
                indicator_name=item.indicator_name,
                category=item.category.value,
                description=item.description,
                expected_unit=item.expected_unit,
                marketmind_dimension=item.marketmind_dimension.value if item.marketmind_dimension else None,
                un_indicator_id=item.un_indicator_id,
                un_location_id=item.un_location_id,
                default_variant_id=item.default_variant_id,
                default_age_id=item.default_age_id,
                default_sex_id=item.default_sex_id,
                default_category_id=item.default_category_id,
                is_active=item.is_active,
            )
            created_ids.append(str(indicator.id))
        self._session.commit()
        return StandardResponse(
            request=request.model_dump(),
            metadata=MetadataResponse(endpoint="indicators_catalog", records=len(created_ids), stored=True, status="success"),
            data={"indicator_ids": created_ids},
        )

    def list_indicators(self) -> StandardResponse:
        indicators = self._indicator_repo.get_all()
        return StandardResponse(
            request={},
            metadata=MetadataResponse(endpoint="indicators_catalog", records=len(indicators), status="success"),
            data={"indicators": [IndicatorCatalogResponse(id=i.id, indicator_code=i.indicator_code, indicator_name=i.indicator_name, description=i.description, category=i.category, expected_unit=i.expected_unit, marketmind_dimension=i.marketmind_dimension, un_indicator_id=i.un_indicator_id, un_location_id=i.un_location_id, default_variant_id=i.default_variant_id, default_age_id=i.default_age_id, default_sex_id=i.default_sex_id, default_category_id=i.default_category_id, is_active=i.is_active, created_at=i.created_at).model_dump() for i in indicators]},
        )

    # ── Collect Indicators ──

    def collect_indicators(self, request: CollectIndicatorsRequest) -> StandardResponse:
        all_observations: list[dict[str, Any]] = []
        errors: list[str] = []
        run_ids: list[str] = []
        request_ids: list[str] = []

        for code in request.indicator_codes:
            indicator = self._indicator_repo.get_by_code(code)
            if not indicator:
                errors.append(f"Indicator {code} not found in catalog")
                continue
            if not indicator.un_indicator_id:
                errors.append(f"Indicator {code} has no un_indicator_id configured")
                continue

            start = utc_now()
            run = self._ingestion_repo.create(source="united_nations_data", request_payload={
                "country": request.country, "location_id": request.location_id,
                "indicator_code": code, "un_indicator_id": indicator.un_indicator_id,
                "start_year": request.start_year, "end_year": request.end_year,
            })
            base_url = f"{settings.undata_api_base_url}/data/indicators/{indicator.un_indicator_id}/locations/{request.location_id}/years/..."
            undata_req = self._request_repo.create(
                ingestion_run_id=run.id, endpoint="indicators_collect", url=base_url,
                request_method=RequestMethod.GET, dataset_id="UN_WPP", dataflow_id="WPP2024",
                country=request.country, indicator_code=code,
                start_period=str(request.start_year), end_period=str(request.end_year),
                query_params={"un_indicator_id": indicator.un_indicator_id, "location_id": request.location_id,
                              "variant_id": indicator.default_variant_id, "age_id": indicator.default_age_id,
                              "sex_id": indicator.default_sex_id, "category_id": indicator.default_category_id},
            )

            try:
                data_rows, raw_rows = self._client.get_data_range(
                    indicator_id=indicator.un_indicator_id, location_id=request.location_id,
                    start_year=request.start_year, end_year=request.end_year,
                    variant_id=indicator.default_variant_id, age_id=indicator.default_age_id,
                    sex_id=indicator.default_sex_id, category_id=indicator.default_category_id,
                )

                self._raw_response_repo.create(
                    undata_request_id=undata_req.id, endpoint="indicators_collect",
                    request_payload={"un_indicator_id": indicator.un_indicator_id, "location_id": request.location_id, "years": f"{request.start_year}-{request.end_year}"},
                    response_payload=raw_rows, response_text=json.dumps(raw_rows),
                )

                raw_observations = [
                    {"country": request.country, "country_name": row.get("location", request.country),
                     "indicator_code": code, "indicator_name": indicator.indicator_name,
                     "time_period": str(row.get("timeLabel", "")), "value": row.get("value"),
                     "unit": indicator.expected_unit, "frequency": "A",
                     "attributes": {"variant": row.get("variant"), "sex": row.get("sex"), "age": row.get("ageLabel"), "source": "UN Population Division Data Portal API"}}
                    for row in data_rows
                ]
                observations = normalize_observations(raw_observations)

                if observations:
                    self._observation_repo.bulk_create(undata_request_id=undata_req.id, observations=observations, dataset_id="UN_WPP", dataflow_id="WPP2024")

                exec_time = elapsed_ms(start)
                self._ingestion_repo.mark_success(run, exec_time)
                self._session.commit()
                run_ids.append(str(run.id))
                request_ids.append(str(undata_req.id))
                all_observations.extend([ObservationResponse(country=o["country"], country_name=o.get("country_name"), indicator_code=o["indicator_code"], indicator_name=o.get("indicator_name"), time_period=o["time_period"], value=o.get("value"), unit=o.get("unit"), frequency=o.get("frequency")).model_dump() for o in observations])
                logger.info(f"endpoint=indicators_collect | ingestion_run_id={run.id} | country={request.country} | indicator={code} | records={len(observations)} | status=success")

            except UNDataBaseException as e:
                exec_time = elapsed_ms(start)
                self._raw_response_repo.create(undata_request_id=undata_req.id, endpoint="indicators_collect", request_payload={"indicator": code}, response_payload={"error": str(e)}, response_text=str(e))
                self._ingestion_repo.mark_failed(run, str(e), exec_time)
                self._session.commit()
                errors.append(f"Failed collecting {code}: {e}")
            except Exception as e:
                exec_time = elapsed_ms(start)
                self._raw_response_repo.create(undata_request_id=undata_req.id, endpoint="indicators_collect", request_payload={"indicator": code}, response_payload={"error": str(e)}, response_text=str(e))
                self._ingestion_repo.mark_failed(run, str(e), exec_time)
                self._session.commit()
                errors.append(f"Failed collecting {code}: {e}")

        if errors and not all_observations:
            raise IndicatorNotConfiguredError("; ".join(errors))

        status = "success" if not errors else "partial"
        return StandardResponse(
            request=request.model_dump(),
            metadata=MetadataResponse(endpoint="indicators_collect", records=len(all_observations), stored=True, status=status, collected_at=utc_now()),
            data={"observations": all_observations, "errors": errors if errors else None, "ingestion_run_ids": run_ids, "undata_request_ids": request_ids},
        )

    # ── Lookups ──

    def get_request(self, undata_request_id: uuid.UUID) -> StandardResponse:
        req = self._request_repo.get_by_id(undata_request_id)
        if not req:
            raise ResourceNotFoundError(f"UNData request {undata_request_id} not found")
        observations = self._observation_repo.get_by_request_id(undata_request_id)
        return StandardResponse(
            request={"undata_request_id": str(undata_request_id)},
            metadata=MetadataResponse(endpoint="requests", records=len(observations), status="success", ingestion_run_id=req.ingestion_run_id, undata_request_id=req.id),
            data={"request": UNDataRequestResponse(id=req.id, ingestion_run_id=req.ingestion_run_id, endpoint=req.endpoint, url=req.url, dataset_id=req.dataset_id, dataflow_id=req.dataflow_id, country=req.country, indicator_code=req.indicator_code, start_period=req.start_period, end_period=req.end_period, request_method=req.request_method, created_at=req.created_at).model_dump(),
                  "observations": [ObservationResponse(country=o.country, country_name=o.country_name, indicator_code=o.indicator_code, indicator_name=o.indicator_name, time_period=o.time_period, value=o.value, unit=o.unit, frequency=o.frequency).model_dump() for o in observations]},
        )

    def get_run(self, ingestion_run_id: uuid.UUID) -> StandardResponse:
        run = self._ingestion_repo.get_by_id(ingestion_run_id)
        if not run:
            raise ResourceNotFoundError(f"Ingestion run {ingestion_run_id} not found")
        return StandardResponse(
            request={"ingestion_run_id": str(ingestion_run_id)},
            metadata=MetadataResponse(endpoint="runs", status="success", ingestion_run_id=run.id),
            data={"run": IngestionRunResponse(id=run.id, source=run.source, status=run.status, started_at=run.started_at, finished_at=run.finished_at, execution_time_ms=run.execution_time_ms, request_payload=run.request_payload, error_message=run.error_message, created_at=run.created_at).model_dump()},
        )
