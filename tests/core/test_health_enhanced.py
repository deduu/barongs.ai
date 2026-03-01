from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.models.config import AppSettings
from src.core.server.factory import create_app


@pytest.fixture
def settings() -> AppSettings:
    return AppSettings(app_name="test", api_key="k", debug=False)


class TestHealthEndpoints:
    async def test_liveness_always_ok(self, settings: AppSettings):
        app = create_app(settings)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

    async def test_ready_ok_with_no_checks(self, settings: AppSettings):
        app = create_app(settings)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ready")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ready"

    async def test_ready_ok_when_all_checks_pass(self, settings: AppSettings):
        app = create_app(settings)
        app.state.readiness_checks = [
            ("postgres", AsyncMock(return_value=True)),
            ("redis", AsyncMock(return_value=True)),
        ]
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ready")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "ready"
            assert body["checks"]["postgres"] == "ok"
            assert body["checks"]["redis"] == "ok"

    async def test_ready_degraded_when_check_fails(self, settings: AppSettings):
        app = create_app(settings)
        app.state.readiness_checks = [
            ("postgres", AsyncMock(return_value=True)),
            ("redis", AsyncMock(return_value=False)),
        ]
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ready")
            assert resp.status_code == 503
            body = resp.json()
            assert body["status"] == "degraded"
            assert body["checks"]["postgres"] == "ok"
            assert body["checks"]["redis"] == "failing"

    async def test_ready_degraded_when_check_raises(self, settings: AppSettings):
        app = create_app(settings)
        app.state.readiness_checks = [
            ("postgres", AsyncMock(side_effect=ConnectionError("refused"))),
        ]
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ready")
            assert resp.status_code == 503
            body = resp.json()
            assert body["status"] == "degraded"
            assert body["checks"]["postgres"] == "failing"
