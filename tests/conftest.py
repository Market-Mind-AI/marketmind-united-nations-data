from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app


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
