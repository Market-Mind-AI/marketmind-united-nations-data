from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """A espera entre tentativas é real (app/utils/retry.py); nos testes ela
    seria só tempo perdido. A contagem de tentativas continua valendo."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "default_backoff", 0)


@pytest.fixture
def mock_session() -> MagicMock:
    session = MagicMock(spec=Session)
    session.flush = MagicMock()
    session.commit = MagicMock()
    session.execute = MagicMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    return session


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
