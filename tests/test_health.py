from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    mock_session = MagicMock()
    mock_session.execute = MagicMock()

    def session_override():  # type: ignore[no-untyped-def]
        yield mock_session

    with patch("app.api.routes.health.get_db", session_override):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "marketmind-united-nations-data"


def test_version_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "marketmind-united-nations-data"
    assert "version" in data


def test_healthz_answers_without_touching_the_database() -> None:
    """What a liveness probe asks: can THIS process still answer. It must not
    depend on Postgres — a probe that does restarts the pod because the database
    is slow, which fixes nothing and throws away whatever was in flight.

    No database fixture here, deliberately: if this endpoint ever starts needing
    one, this test fails.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
