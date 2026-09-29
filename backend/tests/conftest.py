from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401  (registers tables)
from app.config import settings
from app.database import get_session
from app.main import app


@pytest.fixture(autouse=True)
def no_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests always use the deterministic rule-based fallback."""
    monkeypatch.setattr(settings, "groq_api_key", None)


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def override_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def send(client: TestClient) -> Callable[..., dict[str, Any]]:
    counter = iter(range(1, 10_000))

    def _send(
        text: str,
        sender: tuple[str, str] = ("u_101", "Rohan"),
        target: tuple[str, str] | None = ("u_202", "Aman"),
    ) -> dict[str, Any]:
        payload = {
            "message_id": f"msg_{next(counter):03d}",
            "sender": {"id": sender[0], "name": sender[1]},
            "target": {"id": target[0], "name": target[1]} if target else None,
            "text": text,
            "timestamp": "2026-09-30T00:55:00Z",
        }
        response = client.post("/api/v1/messages/classify", json=payload)
        assert response.status_code == 200, response.text
        return response.json()

    return _send
