from unittest.mock import MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_undata_service
from app.main import app
from app.schemas.responses import MetadataResponse, StandardResponse

MOCK_LIST = StandardResponse(request={}, metadata=MetadataResponse(endpoint="test", records=0, status="success"), data={"items": []})
MOCK_COLLECT = StandardResponse(
    request={},
    metadata=MetadataResponse(endpoint="indicators_collect", execution_time_ms=100, records=1, stored=True, status="success", ingestion_run_id=uuid4(), undata_request_id=uuid4()),
    data={"observations": [{"country": "ES", "indicator_code": "TOTAL_POPULATION", "time_period": "2020", "value": 47000000, "unit": "persons", "frequency": "A"}]},
)


def _mock_service() -> MagicMock:
    s = MagicMock()
    s.get_remote_indicators.return_value = MOCK_LIST
    s.get_remote_locations.return_value = MOCK_LIST
    s.register_dataflows.return_value = MOCK_LIST
    s.list_dataflows.return_value = MOCK_LIST
    s.register_datastructures.return_value = MOCK_LIST
    s.list_datastructures.return_value = MOCK_LIST
    s.register_indicators.return_value = MOCK_LIST
    s.list_indicators.return_value = MOCK_LIST
    s.collect_indicators.return_value = MOCK_COLLECT
    s.get_request.return_value = MOCK_LIST
    s.get_run.return_value = MOCK_LIST
    return s


_svc = _mock_service()


def _override() -> MagicMock:  # type: ignore[misc]
    return _svc


def _test(method: str, path: str, json: dict | None = None) -> None:
    app.dependency_overrides[get_undata_service] = _override
    try:
        client = TestClient(app)
        resp = getattr(client, method)(path, json=json) if json else getattr(client, method)(path)
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


class TestRemoteEndpoints:
    def test_remote_indicators(self) -> None:
        _test("get", "/remote/indicators")

    def test_remote_locations(self) -> None:
        _test("get", "/remote/locations")


class TestDataflowEndpoints:
    def test_register(self) -> None:
        _test("post", "/dataflows/register", {"dataflows": [{"dataflow_id": "WPP", "name": "Pop"}]})

    def test_list(self) -> None:
        _test("get", "/dataflows")


class TestDatastructureEndpoints:
    def test_register(self) -> None:
        _test("post", "/datastructures/register", {"dataflow_id": "WPP", "dimensions": [{"dimension_id": "REF", "codes": []}]})

    def test_list(self) -> None:
        _test("get", "/datastructures")


class TestIndicatorEndpoints:
    def test_register(self) -> None:
        _test("post", "/indicators/catalog", {"indicators": [{"indicator_code": "POP", "indicator_name": "Pop", "category": "total_population", "un_indicator_id": 49}]})

    def test_list(self) -> None:
        _test("get", "/indicators/catalog")

    def test_collect(self) -> None:
        _test("post", "/indicators/collect", {"country": "ES", "location_id": 724, "start_year": 2020, "end_year": 2023, "indicator_codes": ["TOTAL_POPULATION"]})


class TestAuditEndpoints:
    def test_get_request(self) -> None:
        _test("get", f"/requests/{uuid4()}")

    def test_get_run(self) -> None:
        _test("get", f"/runs/{uuid4()}")
