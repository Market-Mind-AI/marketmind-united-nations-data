from enum import StrEnum


class IngestionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class IndicatorCategory(StrEnum):
    TOTAL_POPULATION = "total_population"
    URBAN_POPULATION = "urban_population"
    URBAN_POPULATION_PERCENTAGE = "urban_population_percentage"
    POPULATION_BY_AGE = "population_by_age"
    WORKING_AGE_POPULATION = "working_age_population"
    POPULATION_GROWTH = "population_growth"
    POPULATION_DENSITY = "population_density"
    MIGRATION = "migration"


class MarketMindDimension(StrEnum):
    DEMOGRAPHIC_READINESS = "demographic_readiness"
    MARKET_POPULATION_POTENTIAL = "market_population_potential"
    URBAN_CONSUMPTION_POTENTIAL = "urban_consumption_potential"
    TARGET_AGE_FIT = "target_age_fit"


class RequestMethod(StrEnum):
    GET = "GET"
    POST = "POST"
