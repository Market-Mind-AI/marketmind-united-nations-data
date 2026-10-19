from pydantic import BaseModel, Field, field_validator

from app.domain.enums import IndicatorCategory, MarketMindDimension


class DataflowItem(BaseModel):
    agency_id: str | None = Field(None, examples=["UNPD"])
    dataflow_id: str = Field(..., examples=["WPP2024"])
    name: str | None = Field(None, examples=["World Population Prospects 2024"])
    description: str | None = Field(None)
    version: str | None = Field(None, examples=["2024"])


class RegisterDataflowsRequest(BaseModel):
    dataflows: list[DataflowItem] = Field(..., min_length=1)


class CodeItem(BaseModel):
    code_id: str = Field(..., examples=["724"])
    code_name: str | None = Field(None, examples=["Spain"])


class DimensionItem(BaseModel):
    dimension_id: str = Field(..., examples=["REF_AREA"])
    dimension_name: str | None = Field(None, examples=["Reference area"])
    dimension_position: int | None = Field(None, ge=0, examples=[1])
    codes: list[CodeItem] = Field(default_factory=list)


class RegisterDatastructuresRequest(BaseModel):
    dataflow_id: str = Field(..., examples=["WPP2024"])
    dimensions: list[DimensionItem] = Field(..., min_length=1)


class IndicatorCatalogItem(BaseModel):
    indicator_code: str = Field(..., examples=["TOTAL_POPULATION"])
    indicator_name: str = Field(..., examples=["Total Population"])
    description: str | None = Field(None, examples=["Total resident population by country and year."])
    category: IndicatorCategory = Field(..., examples=[IndicatorCategory.TOTAL_POPULATION])
    expected_unit: str | None = Field(None, examples=["persons"])
    marketmind_dimension: MarketMindDimension | None = Field(
        None, examples=[MarketMindDimension.MARKET_POPULATION_POTENTIAL]
    )
    un_indicator_id: int | None = Field(
        None, examples=[49], description="Indicator ID from UN Population Data Portal API"
    )
    un_location_id: int | None = Field(None, examples=[724], description="Default location ID (e.g. 724=Spain)")
    default_variant_id: int = Field(4, examples=[4], description="Variant ID (4=Medium)")
    default_age_id: int = Field(188, examples=[188], description="Age ID (188=Total)")
    default_sex_id: int = Field(3, examples=[3], description="Sex ID (3=Both sexes)")
    default_category_id: int = Field(0, examples=[0], description="Category ID (0=N/A)")
    is_active: bool = Field(True)


class RegisterIndicatorsCatalogRequest(BaseModel):
    indicators: list[IndicatorCatalogItem] = Field(..., min_length=1)


class CollectIndicatorsRequest(BaseModel):
    country: str = Field(..., min_length=2, max_length=3, examples=["ES"])
    location_id: int = Field(..., examples=[724], description="UN location ID (e.g. 724=Spain, 250=France)")
    start_year: int = Field(..., ge=1950, le=2100, examples=[2015])
    end_year: int = Field(..., ge=1950, le=2100, examples=[2025])
    indicator_codes: list[str] = Field(..., min_length=1, examples=[["TOTAL_POPULATION"]])

    @field_validator("end_year")
    @classmethod
    def validate_years(cls, v: int, info: object) -> int:
        if hasattr(info, "data"):
            data = getattr(info, "data")
            start = data.get("start_year")
            if start is not None and v < start:
                raise ValueError("end_year must be >= start_year")
        return v


class RefreshStaleRequest(BaseModel):
    """Body of the daily maintenance pass. Every field has a default so the
    scheduled call can send `{}`."""

    stale_after_days: int = Field(
        default=30, ge=1, le=3650, description="A country whose last check is older than this gets collected again."
    )
    # Sem teto por padrão: None quer dizer "todo país vencido nesta passagem".
    # Um teto de 10 contra 24 países não conseguia sequer limpar o atraso de uma
    # noite — sobravam 14, que na noite seguinte disputavam as mesmas 10 vagas
    # com os que tinham acabado de vencer. O teto continua disponível para quem
    # quiser limitar uma partida a frio; ele só deixou de ser o padrão.
    limit: int | None = Field(default=None, ge=1, le=200, description="Most countries to refresh in one pass.")
    # Quando ligado, uma passagem que deixou país para trás responde 503 em vez
    # de 200. É o que transforma o CronJob em rede de segurança: `curl --fail`
    # sai diferente de zero, o Kubernetes retenta, e o que não se resolve fica
    # como Job `Failed` em vez de um sucesso que não coletou nada.
    fail_if_incomplete: bool = Field(
        default=False,
        description="Answer 503 when any country failed, so a caller that retries on error can retry.",
    )
    years_back: int = Field(
        default=5, ge=1, le=70, description="How far back the replayed window reaches, counting from this year."
    )
