import pytest
from pydantic import ValidationError

from app.domain.enums import IndicatorCategory, MarketMindDimension
from app.schemas.requests import (
    CollectIndicatorsRequest,
    RegisterDataflowsRequest,
    RegisterIndicatorsCatalogRequest,
)


class TestCollectIndicatorsRequest:
    def test_valid_request(self) -> None:
        req = CollectIndicatorsRequest(country="ES", location_id=724, start_year=2020, end_year=2025, indicator_codes=["TOTAL_POPULATION"])
        assert req.country == "ES"
        assert req.location_id == 724

    def test_country_min_length(self) -> None:
        with pytest.raises(ValidationError):
            CollectIndicatorsRequest(country="E", location_id=724, start_year=2020, end_year=2025, indicator_codes=["X"])

    def test_empty_indicator_codes(self) -> None:
        with pytest.raises(ValidationError):
            CollectIndicatorsRequest(country="ES", location_id=724, start_year=2020, end_year=2025, indicator_codes=[])

    def test_end_before_start(self) -> None:
        with pytest.raises(ValidationError):
            CollectIndicatorsRequest(country="ES", location_id=724, start_year=2025, end_year=2020, indicator_codes=["X"])


class TestRegisterDataflowsRequest:
    def test_valid_request(self) -> None:
        req = RegisterDataflowsRequest(dataflows=[{"dataflow_id": "WPP2024", "agency_id": "UNPD", "name": "Population"}])
        assert len(req.dataflows) == 1

    def test_empty_dataflows(self) -> None:
        with pytest.raises(ValidationError):
            RegisterDataflowsRequest(dataflows=[])


class TestRegisterIndicatorsCatalogRequest:
    def test_valid_request(self) -> None:
        req = RegisterIndicatorsCatalogRequest(indicators=[{
            "indicator_code": "TOTAL_POP", "indicator_name": "Total Population",
            "category": IndicatorCategory.TOTAL_POPULATION,
            "marketmind_dimension": MarketMindDimension.MARKET_POPULATION_POTENTIAL,
            "un_indicator_id": 49,
        }])
        assert len(req.indicators) == 1
        assert req.indicators[0].un_indicator_id == 49
        assert req.indicators[0].default_variant_id == 4
        assert req.indicators[0].default_age_id == 188
        assert req.indicators[0].default_sex_id == 3
