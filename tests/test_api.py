"""Checks the HTTP endpoint makes before any model call. Skipped where FastAPI is not installed."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from emporio import api  # noqa: E402

client = TestClient(api.app)
MESSAGE = {"from": "+55 67 90000-0000", "text": "Oi"}


def test_token_is_required_when_configured(monkeypatch):
    monkeypatch.setenv("EMPORIO_API_TOKEN", "t0ken-for-tests")
    assert client.post("/whatsapp/messages", json=MESSAGE).status_code == 401
    wrong = {"Authorization": "Bearer nope"}
    assert client.post("/whatsapp/messages", json=MESSAGE, headers=wrong).status_code == 401


def test_oversized_or_empty_messages_never_reach_the_model(monkeypatch):
    monkeypatch.delenv("EMPORIO_API_TOKEN", raising=False)
    for text in ("x" * 4097, ""):
        assert client.post("/whatsapp/messages", json={**MESSAGE, "text": text}).status_code == 422


def test_health():
    assert client.get("/health").json() == {"status": "ok"}
