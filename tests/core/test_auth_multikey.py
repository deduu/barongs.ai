"""Tests for multi-key auth returning AuthContext."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.core.middleware.auth import create_api_key_dependency
from src.core.models.auth import AuthContext
from src.core.models.config import AppSettings


def _make_app(
    api_key: str = "test-key",
    api_keys: dict[str, str] | None = None,
) -> FastAPI:
    settings = AppSettings(api_key=api_key, api_keys=api_keys or {})
    verify = create_api_key_dependency(settings)

    app = FastAPI()

    @app.get("/protected")
    async def protected(auth: AuthContext = Depends(verify)) -> dict[str, str | None]:
        return {
            "tenant_id": auth.tenant_id,
            "api_key": auth.api_key,
            "user_id": auth.user_id,
        }

    return app


class TestSingleKeyMode:
    """Backward-compatible single-key mode (api_keys empty)."""

    def test_valid_key_returns_auth_context(self) -> None:
        client = TestClient(_make_app("my-secret"))
        resp = client.get("/protected", headers={"X-API-Key": "my-secret"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["tenant_id"] == "default"
        assert body["api_key"] == "my-secret"

    def test_valid_bearer_returns_auth_context(self) -> None:
        client = TestClient(_make_app("my-secret"))
        resp = client.get(
            "/protected", headers={"Authorization": "Bearer my-secret"}
        )
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == "default"

    def test_invalid_key_returns_403(self) -> None:
        client = TestClient(_make_app("correct"))
        resp = client.get("/protected", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 403

    def test_missing_key_returns_401(self) -> None:
        client = TestClient(_make_app())
        resp = client.get("/protected")
        assert resp.status_code == 401


class TestMultiKeyMode:
    """Multi-key mode (api_keys populated)."""

    def test_resolves_tenant_from_key(self) -> None:
        keys = {"sk-abc": "tenant-acme", "sk-def": "tenant-globex"}
        client = TestClient(_make_app(api_keys=keys))
        resp = client.get("/protected", headers={"X-API-Key": "sk-abc"})
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == "tenant-acme"

    def test_different_key_resolves_different_tenant(self) -> None:
        keys = {"sk-abc": "tenant-acme", "sk-def": "tenant-globex"}
        client = TestClient(_make_app(api_keys=keys))
        resp = client.get("/protected", headers={"X-API-Key": "sk-def"})
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == "tenant-globex"

    def test_unknown_key_returns_403(self) -> None:
        keys = {"sk-abc": "tenant-acme"}
        client = TestClient(_make_app(api_keys=keys))
        resp = client.get("/protected", headers={"X-API-Key": "sk-unknown"})
        assert resp.status_code == 403

    def test_missing_key_returns_401(self) -> None:
        keys = {"sk-abc": "tenant-acme"}
        client = TestClient(_make_app(api_keys=keys))
        resp = client.get("/protected")
        assert resp.status_code == 401

    def test_bearer_works_in_multi_key_mode(self) -> None:
        keys = {"sk-abc": "tenant-acme"}
        client = TestClient(_make_app(api_keys=keys))
        resp = client.get(
            "/protected", headers={"Authorization": "Bearer sk-abc"}
        )
        assert resp.status_code == 200
        assert resp.json()["tenant_id"] == "tenant-acme"

    def test_single_api_key_ignored_when_api_keys_set(self) -> None:
        """When api_keys is populated, the single api_key field is ignored."""
        keys = {"sk-multi": "tenant-x"}
        client = TestClient(_make_app(api_key="single-key", api_keys=keys))
        # The single key should NOT work
        resp = client.get("/protected", headers={"X-API-Key": "single-key"})
        assert resp.status_code == 403
