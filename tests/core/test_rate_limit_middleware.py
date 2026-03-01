from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from src.core.models.config import AppSettings
from src.core.server.factory import create_app


def _make_app(max_tokens: int = 3, window_seconds: int = 60) -> tuple:
    settings = AppSettings(
        app_name="test",
        api_key="test-key",
        debug=False,
        rate_limit_requests=max_tokens,
        rate_limit_window_seconds=window_seconds,
    )
    app = create_app(settings)

    @app.get("/api/test")
    async def test_endpoint():
        return {"ok": True}

    return app, settings


class TestRateLimitMiddleware:
    async def test_allows_requests_under_limit(self):
        app, _ = _make_app(max_tokens=5)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for _ in range(5):
                resp = await client.get("/api/test")
                assert resp.status_code == 200

    async def test_blocks_after_limit_exceeded(self):
        app, _ = _make_app(max_tokens=2)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First 2 requests succeed
            for _ in range(2):
                resp = await client.get("/api/test")
                assert resp.status_code == 200

            # 3rd request should be rate limited
            resp = await client.get("/api/test")
            assert resp.status_code == 429
            body = resp.json()
            assert body["error"] == "rate_limit_exceeded"
            assert "Retry-After" in resp.headers

    async def test_health_endpoint_exempt(self):
        app, _ = _make_app(max_tokens=1)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Exhaust the rate limit
            resp = await client.get("/api/test")
            assert resp.status_code == 200

            # Health endpoints should still work
            resp = await client.get("/health")
            assert resp.status_code == 200

            resp = await client.get("/ready")
            assert resp.status_code == 200

    async def test_rate_limit_per_client(self):
        app, _ = _make_app(max_tokens=1)
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Client A uses their limit
            resp = await client.get(
                "/api/test", headers={"X-API-Key": "key-a"}
            )
            assert resp.status_code == 200

            # Client A is blocked
            resp = await client.get(
                "/api/test", headers={"X-API-Key": "key-a"}
            )
            assert resp.status_code == 429

            # Client B still has their own bucket
            resp = await client.get(
                "/api/test", headers={"X-API-Key": "key-b"}
            )
            assert resp.status_code == 200
