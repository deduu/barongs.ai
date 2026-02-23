from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.middleware.circuit_breaker import CircuitBreakerError
from src.core.middleware.rate_limiter import RateLimitExceededError
from src.core.middleware.timeout import TimeoutError


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
