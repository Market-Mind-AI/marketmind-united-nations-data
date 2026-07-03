import math
from decimal import Decimal, InvalidOperation
from typing import Any


def clean_value(val: Any) -> Decimal | None:
    if val is None or val == "" or val == "NaN":
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    try:
        d = Decimal(str(val))
        if d.is_nan() or d.is_infinite():
            return None
        return d
    except (InvalidOperation, ValueError, TypeError):
        return None


def clean_string(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def ensure_list(val: Any) -> list[Any]:
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def normalize_observations(raw_observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for obs in raw_observations:
        normalized.append(
            {
                "country": str(obs.get("country", "UNKNOWN")),
                "country_name": clean_string(obs.get("country_name")),
                "indicator_code": str(obs.get("indicator_code", "UNKNOWN")),
                "indicator_name": clean_string(obs.get("indicator_name")),
                "time_period": str(obs.get("time_period", "UNKNOWN")),
                "value": clean_value(obs.get("value")),
                "unit": clean_string(obs.get("unit")),
                "frequency": clean_string(obs.get("frequency")),
                "attributes": obs.get("attributes"),
            }
        )
    return normalized
