from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.core.llm.errors import LLMProviderError, LLMTimeoutError
from src.core.middleware.circuit_breaker import CircuitBreakerError
from src.core.middleware.rate_limiter import RateLimitExceededError
from src.core.middleware.timeout import TimeoutError

logger = logging.getLogger(__name__)


class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    """Catch-all middleware for unhandled exceptions.

    Returns a structured JSON 500 response instead of leaking stack traces.
    Must be added BEFORE other middleware so it wraps everything.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "detail": "An unexpected error occurred.",
                },
            )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(TimeoutError)
    async def timeout_handler(request: Request, exc: TimeoutError) -> JSONResponse:
        return JSONResponse(
            status_code=504,
            content={
                "error": "timeout",
                "detail": f"{exc.operation} timed out after {exc.timeout}s",
            },
        )

    @app.exception_handler(CircuitBreakerError)
    async def circuit_breaker_handler(request: Request, exc: CircuitBreakerError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "error": "service_unavailable",
                "detail": str(exc),
            },
        )

    @app.exception_handler(RateLimitExceededError)
    async def rate_limit_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "detail": str(exc),
            },
            headers={"Retry-After": str(int(exc.retry_after) + 1)},
        )

    @app.exception_handler(LLMTimeoutError)
    async def llm_timeout_handler(request: Request, exc: LLMTimeoutError) -> JSONResponse:
        return JSONResponse(
            status_code=504,
            content={
                "error": "llm_timeout",
                "detail": str(exc),
            },
        )

    @app.exception_handler(LLMProviderError)
    async def llm_provider_handler(request: Request, exc: LLMProviderError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={
                "error": "llm_provider_error",
                "detail": str(exc),
            },
        )
