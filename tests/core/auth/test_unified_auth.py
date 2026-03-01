"""Tests for unified auth dependency (JWT + API-key fallback)."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.core.auth.jwt import create_access_token
from src.core.middleware.auth import create_unified_auth_dependency
from src.core.models.auth import AuthContext
from src.core.models.config import AppSettings


def _make_app(settings: AppSettings) -> FastAPI:
    app = FastAPI()
    dep = create_unified_auth_dependency(settings)

    @app.get("/test")
    async def test_route(auth: AuthContext = Depends(dep)):
        return {
            "tenant_id": auth.tenant_id,
            "user_id": auth.user_id,
            "auth_method": auth.auth_method,
        }

    return app


def test_jwt_auth():
    settings = AppSettings(
        user_auth_enabled=True,
        jwt_secret_key="test-secret",
        api_key="some-api-key",
        environment="development",
    )
    client = TestClient(_make_app(settings))

    token = create_access_token(
        user_id="u1",
        tenant_id="t1",
        email="test@example.com",
        secret_key="test-secret",
    )

    resp = client.get("/test", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["auth_method"] == "jwt"
    assert data["user_id"] == "u1"
    assert data["tenant_id"] == "t1"


def test_api_key_fallback():
    settings = AppSettings(
        user_auth_enabled=True,
        jwt_secret_key="test-secret",
        api_key="my-api-key",
        environment="development",
    )
    client = TestClient(_make_app(settings))

    resp = client.get("/test", headers={"X-API-Key": "my-api-key"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["auth_method"] == "api_key"
    assert data["tenant_id"] == "default"


def test_bearer_api_key_no_dots():
    """An API key without dots in Bearer header should resolve via API key logic."""
    settings = AppSettings(
        user_auth_enabled=True,
        jwt_secret_key="test-secret",
        api_key="my-api-key-no-dots",
        environment="development",
    )
    client = TestClient(_make_app(settings))

    resp = client.get("/test", headers={"Authorization": "Bearer my-api-key-no-dots"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["auth_method"] == "api_key"


def test_invalid_jwt_falls_back_to_api_key():
    """Invalid JWT token falls through to API key validation."""
    settings = AppSettings(
        user_auth_enabled=True,
        jwt_secret_key="test-secret",
        api_keys={"bad.jwt.token": "tenant-x"},
        environment="development",
    )
    client = TestClient(_make_app(settings))

    resp = client.get("/test", headers={"Authorization": "Bearer bad.jwt.token"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["auth_method"] == "api_key"
    assert data["tenant_id"] == "tenant-x"


def test_user_auth_disabled_uses_api_key():
    settings = AppSettings(
        user_auth_enabled=False,
        api_key="my-key",
        environment="development",
    )
    client = TestClient(_make_app(settings))

    resp = client.get("/test", headers={"Authorization": "Bearer my-key"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["auth_method"] == "api_key"


def test_no_credentials_returns_401():
    settings = AppSettings(
        user_auth_enabled=True,
        jwt_secret_key="test-secret",
        api_key="my-key",
        environment="development",
    )
    client = TestClient(_make_app(settings))

    resp = client.get("/test")
    assert resp.status_code == 401
