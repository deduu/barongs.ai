from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.core.models.config import AppSettings
from src.core.server.openai_compat.auth import create_bearer_auth_dependency


def _make_app(
    api_key: str = "test-key",
    *,
    openai_auth_enabled: bool = True,
) -> FastAPI:
    """Create a minimal app with a bearer-auth-protected endpoint."""
    settings = AppSettings(api_key=api_key, openai_auth_enabled=openai_auth_enabled)
    verify = create_bearer_auth_dependency(settings)

    app = FastAPI()

    @app.get("/protected")
    async def protected(token: str = Depends(verify)) -> dict[str, str]:
        return {"token": token}

    return app


class TestBearerAuth:
    def test_valid_bearer_token(self) -> None:
        client = TestClient(_make_app("my-secret"))
        resp = client.get(
            "/protected", headers={"Authorization": "Bearer my-secret"}
        )
        assert resp.status_code == 200
        assert resp.json()["token"] == "my-secret"

    def test_missing_auth_header(self) -> None:
        client = TestClient(_make_app())
        resp = client.get("/protected")
        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body["detail"]
        assert body["detail"]["error"]["type"] == "auth_error"

    def test_invalid_bearer_token(self) -> None:
        client = TestClient(_make_app("correct-key"))
        resp = client.get(
            "/protected", headers={"Authorization": "Bearer wrong-key"}
        )
        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body["detail"]
        assert body["detail"]["error"]["code"] == "invalid_api_key"

    def test_error_is_openai_format(self) -> None:
        client = TestClient(_make_app())
        resp = client.get("/protected")
        body = resp.json()
        # OpenAI error format: {"detail": {"error": {"message": ..., "type": ..., "code": ...}}}
        error = body["detail"]["error"]
        assert "message" in error
        assert "type" in error
        assert "code" in error


class TestBearerAuthDisabled:
    def test_no_auth_header_succeeds(self) -> None:
        client = TestClient(_make_app(openai_auth_enabled=False))
        resp = client.get("/protected")
        assert resp.status_code == 200

    def test_with_auth_header_also_succeeds(self) -> None:
        client = TestClient(_make_app(openai_auth_enabled=False))
        resp = client.get(
            "/protected", headers={"Authorization": "Bearer anything"}
        )
        assert resp.status_code == 200
