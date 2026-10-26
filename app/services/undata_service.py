import json
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.clients.undata_client import UNDataClient
from app.core.config import settings
from app.core.exceptions import (
    IndicatorNotConfiguredError,
    ResourceNotFoundError,
    UNDataBaseException,
    UNDataClientError,
    UNDataEmptyResponseError,
    UNDataTransientError,
)
from app.core.logging import logger
from app.domain.enums import IndicatorCategory, MarketMindDimension, RequestMethod
from app.repositories.freshness_repository import FreshnessRepository
from app.repositories.ingestion_run_repository import IngestionRunRepository
from app.repositories.raw_api_response_repository import RawApiResponseRepository
from app.repositories.undata_dataflow_repository import UNDataDataflowRepository
from app.repositories.undata_datastructure_repository import UNDataDatastructureRepository
from app.repositories.undata_indicator_repository import UNDataIndicatorRepository
from app.repositories.undata_observation_repository import UNDataObservationRepository
from app.repositories.undata_request_repository import UNDataRequestRepository
from app.schemas.requests import (
    CollectIndicatorsRequest,
    IndicatorCatalogItem,
    RefreshStaleRequest,
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

# un_indicator_id values confirmed 2026-07-09 against the real UN Population
# Data Portal API (GET /remote/indicators), NOT guessed — the IDs matter:
#   49 = "Total population by sex"      (TOTAL_POPULATION)
#   67 = "Median age of population"     (MEDIAN_AGE)
#   65 = "Total net-migration"          (NET_MIGRATION — absolute count; the
#        Net Migration Rate Score divides this by TOTAL_POPULATION itself)
#   51 = "Rate of population change"    (POPULATION_GROWTH — annual %)
# An earlier draft wrongly mapped NET_MIGRATION to 51 (population change
# rate), which produced absurd net-migration-rate values (~1e-6) and left
# POPULATION_GROWTH unseeded entirely — both found in the live /analyze test.
SEED_INDICATORS: list[IndicatorCatalogItem] = [
    IndicatorCatalogItem(
        indicator_code="TOTAL_POPULATION",
        indicator_name="Total Population",
        description="Total resident population by country and year.",
        category=IndicatorCategory.TOTAL_POPULATION,
        expected_unit="persons",
        marketmind_dimension=MarketMindDimension.MARKET_POPULATION_POTENTIAL,
        un_indicator_id=49,
    ),
    IndicatorCatalogItem(
        indicator_code="MEDIAN_AGE",
        indicator_name="Median Age",
        description="Median age of the population, both sexes, total age group.",
        category=IndicatorCategory.POPULATION_BY_AGE,
        expected_unit="years",
        marketmind_dimension=MarketMindDimension.TARGET_AGE_FIT,
        un_indicator_id=67,
    ),
    IndicatorCatalogItem(
        indicator_code="NET_MIGRATION",
        indicator_name="Net Migration",
        description="Total net number of migrants (in-migrants minus out-migrants), absolute count.",
        category=IndicatorCategory.MIGRATION,
        expected_unit="persons",
        marketmind_dimension=MarketMindDimension.DEMOGRAPHIC_READINESS,
        un_indicator_id=65,
    ),
    IndicatorCatalogItem(
        indicator_code="POPULATION_GROWTH",
        indicator_name="Population Growth Rate",
        description="Annual rate of population change (%).",
        category=IndicatorCategory.POPULATION_GROWTH,
        expected_unit="percentage",
        marketmind_dimension=MarketMindDimension.DEMOGRAPHIC_READINESS,
        un_indicator_id=51,
    ),
]


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
        self._freshness_repo = FreshnessRepository(session)

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
            metadata=MetadataResponse(
                endpoint="dataflows_register", records=len(created_ids), stored=True, status="success"
            ),
            data={"dataflow_ids": created_ids},
        )

    def list_dataflows(self) -> StandardResponse:
        dataflows = self._dataflow_repo.get_all()
        return StandardResponse(
            request={},
            metadata=MetadataResponse(endpoint="dataflows", records=len(dataflows), status="success"),
            data={
                "dataflows": [
                    DataflowResponse(
                        id=d.id,
                        agency_id=d.agency_id,
                        dataflow_id=d.dataflow_id,
                        name=d.name,
                        description=d.description,
                        version=d.version,
                        created_at=d.created_at,
                    ).model_dump()
                    for d in dataflows
                ]
            },
        )

    # ── Datastructures ──

    def register_datastructures(self, request: RegisterDatastructuresRequest) -> StandardResponse:
        records = self._datastructure_repo.bulk_create(
            dataflow_id=request.dataflow_id, dimensions=[d.model_dump() for d in request.dimensions]
        )
        self._session.commit()
        return StandardResponse(
            request=request.model_dump(),
            metadata=MetadataResponse(
                endpoint="datastructures_register", records=len(records), stored=True, status="success"
            ),
            data={"records_created": len(records)},
        )

    def list_datastructures(self, dataflow_id: str | None = None) -> StandardResponse:
        structures = (
            self._datastructure_repo.get_by_dataflow(dataflow_id) if dataflow_id else self._datastructure_repo.get_all()
        )
        return StandardResponse(
            request={"dataflow_id": dataflow_id} if dataflow_id else {},
            metadata=MetadataResponse(endpoint="datastructures", records=len(structures), status="success"),
            data={
                "datastructures": [
                    DatastructureResponse(
                        id=s.id,
                        dataflow_id=s.dataflow_id,
                        structure_id=s.structure_id,
                        dimension_id=s.dimension_id,
                        dimension_name=s.dimension_name,
                        dimension_position=s.dimension_position,
                        code_id=s.code_id,
                        code_name=s.code_name,
                        created_at=s.created_at,
                    ).model_dump()
                    for s in structures
                ]
            },
        )

    # ── Indicators Catalog ──

    def seed_catalog(self) -> StandardResponse:
        """Idempotent — upserts SEED_INDICATORS by indicator_code (unlike
        register_indicators, which always inserts). Safe to call on every
        startup, not just after a fresh volume."""
        seeded_ids: list[str] = []
        for item in SEED_INDICATORS:
            indicator = self._indicator_repo.upsert(
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
            seeded_ids.append(str(indicator.id))
        self._session.commit()
        return StandardResponse(
            request={},
            metadata=MetadataResponse(
                endpoint="indicators_catalog_seed", records=len(seeded_ids), stored=True, status="success"
            ),
            data={"indicator_ids": seeded_ids},
        )

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
            metadata=MetadataResponse(
                endpoint="indicators_catalog", records=len(created_ids), stored=True, status="success"
            ),
            data={"indicator_ids": created_ids},
        )

    def list_indicators(self) -> StandardResponse:
        indicators = self._indicator_repo.get_all()
        return StandardResponse(
            request={},
            metadata=MetadataResponse(endpoint="indicators_catalog", records=len(indicators), status="success"),
            data={
                "indicators": [
                    IndicatorCatalogResponse(
                        id=i.id,
                        indicator_code=i.indicator_code,
                        indicator_name=i.indicator_name,
                        description=i.description,
                        category=i.category,
                        expected_unit=i.expected_unit,
                        marketmind_dimension=i.marketmind_dimension,
                        un_indicator_id=i.un_indicator_id,
                        un_location_id=i.un_location_id,
                        default_variant_id=i.default_variant_id,
                        default_age_id=i.default_age_id,
                        default_sex_id=i.default_sex_id,
                        default_category_id=i.default_category_id,
                        is_active=i.is_active,
                        created_at=i.created_at,
                    ).model_dump()
                    for i in indicators
                ]
            },
        )

    # ── Collect Indicators ──

    def _configured_indicators(self, codes: list[str]) -> dict[str, Any]:
        """Os indicadores do catálogo que este pedido nomeia -- ou recusa o pedido.

        Um código que o catálogo não conhece, ou que não tem `un_indicator_id`
        para ser coletado, é erro de quem pediu, e recusar o pedido inteiro com
        422 é a mesma regra nos três coletores de indicadores. Até 26/10/2026
        este serviço coletava os outros e só no fim respondia 422, e a mesma
        situação era 400 na OCDE e 404 no World Bank. A recusa vem antes de
        abrir qualquer execução: não houve coleta, e não há o que registrar.
        """
        catalog: dict[str, Any] = {}
        problems: list[str] = []
        for code in codes:
            indicator = self._indicator_repo.get_by_code(code)
            if not indicator:
                problems.append(f"Indicator {code} not found in catalog")
            elif not indicator.un_indicator_id:
                problems.append(f"Indicator {code} has no un_indicator_id configured")
            else:
                catalog[code] = indicator
        if problems:
            raise IndicatorNotConfiguredError("; ".join(problems))
        return catalog

    @staticmethod
    def _collect_failure(failures: dict[str, Exception]) -> UNDataBaseException:
        """O erro de uma coleta em que NENHUM indicador teve resposta da fonte.

        Uma coleta que não trouxe nada levanta erro -- a mesma regra nos três
        coletores de indicadores:

        - toda falha foi passageira (5xx, 429, timeout, rede): a fonte está
          fora, e o erro é 503 -- "tente de novo", que é o que vale fazer. Até
          22/10/2026 isto era um 422 "indicator not configured", e uma queda de
          50 minutos aparecia como erro de configuração em todo trace e log;
        - alguma falha foi uma resposta definitiva que não serve: 502. Também
          era 422, e não é erro de quem pediu.

        4xx fica só para erro de quem pediu, que é recusado antes de coletar
        (`_configured_indicators`).
        """
        detail = "; ".join(f"{code}: {error}" for code, error in failures.items())
        if all(isinstance(error, UNDataTransientError) for error in failures.values()):
            return UNDataTransientError("UN Data Portal unavailable: " + detail)
        return UNDataClientError("No indicator could be collected: " + detail)

    def collect_indicators(self, request: CollectIndicatorsRequest) -> StandardResponse:
        catalog = self._configured_indicators(request.indicator_codes)
        all_observations: list[dict[str, Any]] = []
        failures: dict[str, Exception] = {}
        run_ids: list[str] = []
        request_ids: list[str] = []

        for code in request.indicator_codes:
            indicator = catalog[code]
            start = utc_now()
            run = self._ingestion_repo.create(
                source="united_nations_data",
                request_payload={
                    "country": request.country,
                    "location_id": request.location_id,
                    "indicator_code": code,
                    "un_indicator_id": indicator.un_indicator_id,
                    "start_year": request.start_year,
                    "end_year": request.end_year,
                },
            )

            try:
                try:
                    data_rows, raw_rows = self._client.get_data_range(
                        indicator_id=indicator.un_indicator_id,
                        location_id=request.location_id,
                        start_year=request.start_year,
                        end_year=request.end_year,
                        variant_id=indicator.default_variant_id,
                        age_id=indicator.default_age_id,
                        sex_id=indicator.default_sex_id,
                        category_id=indicator.default_category_id,
                    )
                except UNDataEmptyResponseError:
                    # A fonte respondeu que não tem: é resposta, conta como
                    # verificação, e não é falha.
                    data_rows, raw_rows = [], []

                # A verificação: a linha de requisição só nasce depois que a
                # fonte respondeu. Um indicador que falhou não ganha linha, e
                # por isso não conta como verificado (FreshnessRepository).
                undata_req = self._request_repo.create(
                    ingestion_run_id=run.id,
                    endpoint="indicators_collect",
                    url=(
                        f"{settings.undata_api_base_url}/data/indicators/{indicator.un_indicator_id}"
                        f"/locations/{request.location_id}/years/..."
                    ),
                    request_method=RequestMethod.GET,
                    dataset_id="UN_WPP",
                    dataflow_id="WPP2024",
                    country=request.country,
                    indicator_code=code,
                    start_period=str(request.start_year),
                    end_period=str(request.end_year),
                    query_params={
                        "un_indicator_id": indicator.un_indicator_id,
                        "location_id": request.location_id,
                        "variant_id": indicator.default_variant_id,
                        "age_id": indicator.default_age_id,
                        "sex_id": indicator.default_sex_id,
                        "category_id": indicator.default_category_id,
                    },
                )
                self._raw_response_repo.create(
                    undata_request_id=undata_req.id,
                    endpoint="indicators_collect",
                    request_payload={
                        "un_indicator_id": indicator.un_indicator_id,
                        "location_id": request.location_id,
                        "years": f"{request.start_year}-{request.end_year}",
                    },
                    response_payload=raw_rows,
                    response_text=json.dumps(raw_rows),
                )

                raw_observations = [
                    {
                        "country": request.country,
                        "country_name": row.get("location", request.country),
                        "indicator_code": code,
                        "indicator_name": indicator.indicator_name,
                        "time_period": str(row.get("timeLabel", "")),
                        "value": row.get("value"),
                        "unit": indicator.expected_unit,
                        "frequency": "A",
                        "attributes": {
                            "variant": row.get("variant"),
                            "sex": row.get("sex"),
                            "age": row.get("ageLabel"),
                            "source": "UN Population Division Data Portal API",
                        },
                    }
                    for row in data_rows
                ]
                observations = normalize_observations(raw_observations)

                if observations:
                    self._observation_repo.replace_periods(
                        undata_request_id=undata_req.id,
                        observations=observations,
                        dataset_id="UN_WPP",
                        dataflow_id="WPP2024",
                    )

                exec_time = elapsed_ms(start)
                self._ingestion_repo.mark_success(run, exec_time)
                self._session.commit()
                run_ids.append(str(run.id))
                request_ids.append(str(undata_req.id))
                all_observations.extend(
                    [
                        ObservationResponse(
                            country=o["country"],
                            country_name=o.get("country_name"),
                            indicator_code=o["indicator_code"],
                            indicator_name=o.get("indicator_name"),
                            time_period=o["time_period"],
                            value=o.get("value"),
                            unit=o.get("unit"),
                            frequency=o.get("frequency"),
                        ).model_dump()
                        for o in observations
                    ]
                )
                logger.info(
                    f"endpoint=indicators_collect | ingestion_run_id={run.id} | country={request.country} "
                    f"| indicator={code} | records={len(observations)} | status=success"
                )

            except Exception as e:
                exec_time = elapsed_ms(start)
                self._ingestion_repo.mark_failed(run, str(e), exec_time)
                self._session.commit()
                failures[code] = e
                logger.warning(
                    f"endpoint=indicators_collect | ingestion_run_id={run.id} | country={request.country} "
                    f"| indicator={code} | status=failed | error={e}"
                )

        if not request_ids:
            raise self._collect_failure(failures)

        errors = [f"Failed collecting {code}: {error}" for code, error in failures.items()]
        return StandardResponse(
            request=request.model_dump(),
            metadata=MetadataResponse(
                endpoint="indicators_collect",
                records=len(all_observations),
                stored=True,
                status="success",
                collected_at=utc_now(),
            ),
            data={
                "observations": all_observations,
                "errors": errors if errors else None,
                "indicators_failed": list(failures),
                "ingestion_run_ids": run_ids,
                "undata_request_ids": request_ids,
            },
        )

    # ── Lookups ──

    def get_request(self, undata_request_id: uuid.UUID) -> StandardResponse:
        req = self._request_repo.get_by_id(undata_request_id)
        if not req:
            raise ResourceNotFoundError(f"UNData request {undata_request_id} not found")
        observations = self._observation_repo.get_by_request_id(undata_request_id)
        return StandardResponse(
            request={"undata_request_id": str(undata_request_id)},
            metadata=MetadataResponse(
                endpoint="requests",
                records=len(observations),
                status="success",
                ingestion_run_id=req.ingestion_run_id,
                undata_request_id=req.id,
            ),
            data={
                "request": UNDataRequestResponse(
                    id=req.id,
                    ingestion_run_id=req.ingestion_run_id,
                    endpoint=req.endpoint,
                    url=req.url,
                    dataset_id=req.dataset_id,
                    dataflow_id=req.dataflow_id,
                    country=req.country,
                    indicator_code=req.indicator_code,
                    start_period=req.start_period,
                    end_period=req.end_period,
                    request_method=req.request_method,
                    created_at=req.created_at,
                ).model_dump(),
                "observations": [
                    ObservationResponse(
                        country=o.country,
                        country_name=o.country_name,
                        indicator_code=o.indicator_code,
                        indicator_name=o.indicator_name,
                        time_period=o.time_period,
                        value=o.value,
                        unit=o.unit,
                        frequency=o.frequency,
                    ).model_dump()
                    for o in observations
                ],
            },
        )

    def get_run(self, ingestion_run_id: uuid.UUID) -> StandardResponse:
        run = self._ingestion_repo.get_by_id(ingestion_run_id)
        if not run:
            raise ResourceNotFoundError(f"Ingestion run {ingestion_run_id} not found")
        return StandardResponse(
            request={"ingestion_run_id": str(ingestion_run_id)},
            metadata=MetadataResponse(endpoint="runs", status="success", ingestion_run_id=run.id),
            data={
                "run": IngestionRunResponse(
                    id=run.id,
                    source=run.source,
                    status=run.status,
                    started_at=run.started_at,
                    finished_at=run.finished_at,
                    execution_time_ms=run.execution_time_ms,
                    request_payload=run.request_payload,
                    error_message=run.error_message,
                    created_at=run.created_at,
                ).model_dump()
            },
        )

    # -- Freshness (what we hold, and when we last looked) --

    def get_freshness(
        self,
        *,
        countries: list[str] | None = None,
        indicators: list[str] | None = None,
        stale_after_days: int = 90,
        only_stale: bool = False,
    ) -> StandardResponse:
        """What this service holds and when it last looked, per country and indicator.

        Reports when we last ASKED the UN, not how recent the returned data is.
        UN Data publishes yearly, so a 2024 population figure is the current one
        rather than a stale one, and a rule written against the datum's own
        period would re-fetch every indicator every day forever.

        Naming BOTH a country and an indicator asks a closed question, so it
        gets a closed answer: every requested pair comes back, including pairs
        never fetched, marked stale with last_checked_at null. An empty list
        would be indistinguishable from "everything is fresh".
        """
        countries = [c.strip().upper() for c in countries if c.strip()] if countries else None
        indicators = [i.strip() for i in indicators if i.strip()] if indicators else None

        checks = self._freshness_repo.last_checks(countries=countries, indicators=indicators)
        observed = self._freshness_repo.observation_facts(countries=countries, indicators=indicators)

        if countries and indicators:
            pairs = [(country, indicator) for country in countries for indicator in indicators]
        else:
            pairs = sorted(set(checks) | set(observed))

        now = utc_now()
        cutoff = now - timedelta(days=stale_after_days)

        items: list[dict[str, Any]] = []
        for country, indicator in pairs:
            last_checked_at = checks.get((country, indicator))
            facts = observed.get((country, indicator))
            stale = last_checked_at is None or last_checked_at < cutoff
            if only_stale and not stale:
                continue
            items.append(
                {
                    "country": country,
                    "indicator_code": indicator,
                    "last_checked_at": last_checked_at,
                    "last_observation_at": facts.last_observation_at if facts else None,
                    "latest_period": facts.latest_period if facts else None,
                    "observation_count": facts.observation_count if facts else 0,
                    "stale": stale,
                }
            )

        return StandardResponse(
            request={
                "countries": countries,
                "indicators": indicators,
                "stale_after_days": stale_after_days,
                "only_stale": only_stale,
            },
            metadata=MetadataResponse(endpoint="freshness", records=len(items), stored=False, status="success"),
            data={"as_of": now, "stale_after_days": stale_after_days, "items": items},
        )

    # -- Read (what was collected, without opening this service's database) --

    def get_series(self, *, country: str, indicator_code: str, limit: int | None = None) -> StandardResponse:
        """One indicator's stored values for one country, newest period first.

        Reading another service's tables directly couples the reader to a schema
        it does not own: a column rename here breaks a calculation there,
        silently and at the worst moment. This is the seam that keeps that from
        happening.

        Values come back as rows, never as an average or a rate. That arithmetic
        is versioned method and belongs to whoever owns the method.

        Omit `limit` when you need the whole series -- lining up two indicators
        year by year needs both in full, since the years they cover need not
        match.
        """
        country = country.strip().upper()
        indicator_code = indicator_code.strip()
        observations = self._observation_repo.series(country=country, indicator_code=indicator_code, limit=limit)
        return StandardResponse(
            request={"country": country, "indicator_code": indicator_code, "limit": limit},
            metadata=MetadataResponse(
                endpoint="observations_series", records=len(observations), stored=False, status="success"
            ),
            data={
                "country": country,
                "indicator_code": indicator_code,
                "points": [
                    {
                        "time_period": o.time_period,
                        "value": o.value,
                        "unit": o.unit,
                        "frequency": o.frequency,
                    }
                    for o in observations
                ],
            },
        )

    # -- Scheduled maintenance (the half of freshness nobody has to ask for) --

    def refresh_stale(self, request: RefreshStaleRequest) -> StandardResponse:
        """Collect again whatever has not been looked at in a while.

        The other half is the on-demand collection: something decides a country
        is needed now and asks. Between the two, what this service holds stays
        current without anyone tracking it from outside -- and a second record
        of what was collected, kept elsewhere, drifts from the tables while the
        tables are the ones that can be wrong in silence.

        Bounded on purpose: a first run against a long-idle database finds every
        country stale at once, and the upstream API has its own patience.

        Each country is REPLAYED from what it was last collected with. That is
        not a shortcut here -- collecting needs a numeric location id that is
        not derivable from the country code this service stores, so replaying is
        what keeps that mapping out of this service entirely.

        Um país só conta como renovado quando TODOS os seus indicadores tiveram
        resposta. Se algum falhou, o país conta como falha, com os códigos no
        detalhe -- é o que faz `fail_if_incomplete` acusar uma queda parcial da
        fonte em vez de deixá-la passar como noite boa. Mesma regra nos três.
        """
        freshness = self.get_freshness(stale_after_days=request.stale_after_days, only_stale=True)

        stale_countries: list[str] = []
        for item in freshness.data["items"]:
            if item["country"] not in stale_countries:
                stale_countries.append(item["country"])

        setups = self._ingestion_repo.last_collect_setup_by_country()
        end_year = utc_now().year
        # A mesma janela que o Core pede: de `years_back` anos atrás até este
        # ano, inclusive (macro_coverage, `_ANNUAL_LOOKBACK_YEARS`).
        start_year = end_year - request.years_back

        outcomes: list[dict[str, Any]] = []
        refreshed = failed = skipped = 0

        for country in stale_countries[: request.limit]:
            setup = setups.get(country)
            if setup is None or not setup.get("location_id") or not setup.get("indicator_codes"):
                skipped += 1
                outcomes.append(
                    {
                        "country": country,
                        "outcome": "skipped",
                        "detail": "no successful collection to replay; collect it once on demand first",
                    }
                )
                continue

            try:
                response = self.collect_indicators(
                    CollectIndicatorsRequest(
                        country=country,
                        location_id=int(setup["location_id"]),
                        start_year=start_year,
                        end_year=end_year,
                        indicator_codes=setup["indicator_codes"],
                    )
                )
            except Exception as exc:  # noqa: BLE001 - one country failing must not end the pass
                failed += 1
                logger.warning(f"Scheduled refresh failed for country={country}: {exc}")
                outcomes.append({"country": country, "outcome": "failed", "detail": str(exc)})
                continue

            not_collected = response.data["indicators_failed"]
            if not_collected:
                failed += 1
                logger.warning(f"Scheduled refresh incomplete for country={country}: {not_collected}")
                outcomes.append(
                    {
                        "country": country,
                        "outcome": "failed",
                        "detail": f"indicators not collected: {', '.join(not_collected)}",
                    }
                )
            else:
                refreshed += 1
                outcomes.append({"country": country, "outcome": "refreshed", "detail": None})

        return StandardResponse(
            request={"stale_after_days": request.stale_after_days, "limit": request.limit},
            metadata=MetadataResponse(
                endpoint="maintenance_refresh_stale", records=len(outcomes), stored=True, status="success"
            ),
            data={
                "stale_after_days": request.stale_after_days,
                "stale_countries": len(stale_countries),
                "attempted": len(outcomes),
                "refreshed": refreshed,
                "failed": failed,
                "skipped": skipped,
                "countries": outcomes,
            },
        )
