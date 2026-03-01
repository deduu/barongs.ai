from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.core.middleware.rate_limiter import TokenBucketRateLimiter

_EXEMPT_PATHS = frozenset({"/health", "/ready"})


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client rate limiting middleware using token bucket algorithm.

    Client is identified by X-API-Key header, falling back to client IP.
    Health and readiness probes are exempt.
    """

    def __init__(self, app: object, max_tokens: int = 100, window_seconds: int = 60) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._limiter = TokenBucketRateLimiter(
            max_tokens=max_tokens, window_seconds=window_seconds
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        client_id = request.headers.get("x-api-key") or (request.client.host if request.client else "unknown")

        if not self._limiter.check(client_id):
            tokens_needed = 1.0 - self._limiter._buckets[client_id]
            retry_after = max(1.0, tokens_needed / self._limiter._refill_rate)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": "Too many requests. Please slow down.",
                },
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

        return await call_next(request)
