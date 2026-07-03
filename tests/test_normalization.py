from decimal import Decimal

from app.utils.normalization import clean_string, clean_value, ensure_list, normalize_observations


class TestCleanValue:
    def test_valid_number(self) -> None:
        assert clean_value("123.45") == Decimal("123.45")

    def test_integer(self) -> None:
        assert clean_value(42) == Decimal("42")

    def test_none(self) -> None:
        assert clean_value(None) is None

    def test_empty_string(self) -> None:
        assert clean_value("") is None

    def test_nan_string(self) -> None:
        assert clean_value("NaN") is None

    def test_float_nan(self) -> None:
        assert clean_value(float("nan")) is None

    def test_float_inf(self) -> None:
        assert clean_value(float("inf")) is None


class TestCleanString:
    def test_normal_string(self) -> None:
        assert clean_string("hello") == "hello"

    def test_none(self) -> None:
        assert clean_string(None) is None

    def test_empty_string(self) -> None:
        assert clean_string("") is None

    def test_whitespace(self) -> None:
        assert clean_string("  ") is None

    def test_strips_whitespace(self) -> None:
        assert clean_string("  hello  ") == "hello"


class TestEnsureList:
    def test_list(self) -> None:
        assert ensure_list([1, 2]) == [1, 2]

    def test_single_value(self) -> None:
        assert ensure_list("a") == ["a"]

    def test_none(self) -> None:
        assert ensure_list(None) == []


class TestNormalizeObservations:
    def test_normalizes_list(self) -> None:
        raw = [
            {
                "country": "ES",
                "indicator_code": "POP",
                "time_period": "2020",
                "value": Decimal("47000000"),
                "unit": "persons",
            }
        ]
        result = normalize_observations(raw)
        assert len(result) == 1
        assert result[0]["country"] == "ES"
        assert result[0]["value"] == Decimal("47000000")

    def test_handles_missing_fields(self) -> None:
        raw = [{"country": "FR", "indicator_code": "GDP", "time_period": "2021"}]
        result = normalize_observations(raw)
        assert result[0]["value"] is None
        assert result[0]["unit"] is None

    def test_empty_list(self) -> None:
        assert normalize_observations([]) == []
