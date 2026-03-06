from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.server.diagnostics import create_diagnostics_router


@pytest.fixture()
def app() -> FastAPI:
    """Minimal FastAPI app with diagnostics router mounted."""
    app = FastAPI()
    app.get("/health")(lambda: {"status": "ok"})
    app.post("/api/search")(lambda: {"result": "ok"})

    router = create_diagnostics_router()
    app.include_router(router)
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_diagnostics_returns_routes(client: TestClient) -> None:
    resp = client.get("/api/diagnostics")
    assert resp.status_code == 200
    body = resp.json()
    assert "routes" in body
    paths = [r["path"] for r in body["routes"]]
    assert "/health" in paths
    assert "/api/search" in paths


def test_diagnostics_routes_include_methods(client: TestClient) -> None:
    resp = client.get("/api/diagnostics")
    body = resp.json()
    search_route = next(r for r in body["routes"] if r["path"] == "/api/search")
    assert "POST" in search_route["methods"]


def test_diagnostics_includes_settings_when_available(client: TestClient, app: FastAPI) -> None:
    from src.core.models.config import AppSettings

    app.state.settings = AppSettings(api_key="super-secret", jwt_secret_key="also-secret")
    resp = client.get("/api/diagnostics")
    body = resp.json()
    assert "settings" in body
    # Secrets must be redacted
    assert body["settings"]["api_key"] == "***REDACTED***"
    assert body["settings"]["jwt_secret_key"] == "***REDACTED***"
    # Non-sensitive values should be present
    assert body["settings"]["environment"] == "development"


def test_diagnostics_no_settings_graceful(client: TestClient) -> None:
    resp = client.get("/api/diagnostics")
    body = resp.json()
    assert body["settings"] is None


def test_diagnostics_includes_features(client: TestClient, app: FastAPI) -> None:
    app.state.features = {"rag": True, "deep_search": False}
    resp = client.get("/api/diagnostics")
    body = resp.json()
    assert body["features"] == {"rag": True, "deep_search": False}


def test_diagnostics_no_features_graceful(client: TestClient) -> None:
    resp = client.get("/api/diagnostics")
    body = resp.json()
    assert body["features"] == {}
