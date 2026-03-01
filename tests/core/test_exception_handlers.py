from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.core.llm.errors import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from src.core.middleware.circuit_breaker import CircuitBreakerError
from src.core.middleware.rate_limiter import RateLimitExceededError
from src.core.middleware.timeout import TimeoutError
from src.core.models.config import AppSettings
from src.core.server.factory import create_app


def _make_app(exc: Exception) -> FastAPI:
    """Create an app via factory that raises the given exception."""
    settings = AppSettings(app_name="test", api_key="k", debug=False)
    app = create_app(settings)

    @app.get("/boom")
    async def boom():
        raise exc

    return app


async def _get(app: FastAPI) -> dict:
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/boom")
        return {"status": resp.status_code, "body": resp.json()}


class TestExistingHandlers:
    async def test_timeout_returns_504(self):
        result = await _get(_make_app(TimeoutError("agent.run", 30.0)))
        assert result["status"] == 504
        assert result["body"]["error"] == "timeout"

    async def test_circuit_breaker_returns_503(self):
        result = await _get(_make_app(CircuitBreakerError("Circuit is open")))
        assert result["status"] == 503
        assert result["body"]["error"] == "service_unavailable"

    async def test_rate_limit_returns_429(self):
        result = await _get(_make_app(RateLimitExceededError(10.0)))
        assert result["status"] == 429
        assert result["body"]["error"] == "rate_limit_exceeded"


class TestLLMProviderErrorHandlers:
    async def test_llm_auth_error_returns_502(self):
        result = await _get(_make_app(LLMAuthenticationError(provider="openai")))
        assert result["status"] == 502
        assert result["body"]["error"] == "llm_provider_error"

    async def test_llm_rate_limit_returns_502_with_retry(self):
        result = await _get(_make_app(LLMRateLimitError(provider="openai", retry_after=5.0)))
        assert result["status"] == 502
        assert result["body"]["error"] == "llm_provider_error"

    async def test_llm_timeout_returns_504(self):
        result = await _get(_make_app(LLMTimeoutError(provider="openai", timeout_seconds=30.0)))
        assert result["status"] == 504
        assert result["body"]["error"] == "llm_timeout"

    async def test_generic_llm_error_returns_502(self):
        result = await _get(
            _make_app(
                LLMProviderError("Server error", provider="openai", status_code=500, retryable=True)
            )
        )
        assert result["status"] == 502
        assert result["body"]["error"] == "llm_provider_error"


class TestGlobalFallbackHandler:
    async def test_unhandled_exception_returns_500(self):
        result = await _get(_make_app(RuntimeError("unexpected crash")))
        assert result["status"] == 500
        assert result["body"]["error"] == "internal_server_error"
        # Must NOT leak internal details
        assert "unexpected crash" not in result["body"].get("detail", "")
