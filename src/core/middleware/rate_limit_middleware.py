from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.core.middleware.rate_limiter import RedisRateLimiter, TokenBucketRateLimiter

_EXEMPT_PATHS = frozenset({"/health", "/ready"})


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client rate limiting middleware using token bucket algorithm.

    Accepts either ``TokenBucketRateLimiter`` (in-memory) or
    ``RedisRateLimiter`` (distributed). When no explicit limiter is
    provided, an in-memory one is created from *max_tokens* and
    *window_seconds*.

    Client is identified by X-API-Key header, falling back to client IP.
    Health and readiness probes are exempt.
    """

    def __init__(
        self,
        app: object,
        max_tokens: int = 100,
        window_seconds: int = 60,
        *,
        limiter: TokenBucketRateLimiter | RedisRateLimiter | None = None,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._limiter: Any = limiter or TokenBucketRateLimiter(
            max_tokens=max_tokens, window_seconds=window_seconds
        )
        self._is_async = isinstance(self._limiter, RedisRateLimiter)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        client_id = request.headers.get("x-api-key") or (
            request.client.host if request.client else "unknown"
        )

        if self._is_async:
            allowed = await self._limiter.check(client_id)
        else:
            allowed = self._limiter.check(client_id)

        if not allowed:
            if self._is_async:
                retry_after = await self._limiter.get_retry_after(client_id)
            else:
                retry_after = self._limiter.get_retry_after(client_id)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": "Too many requests. Please slow down.",
                },
                headers={"Retry-After": str(int(max(1.0, retry_after)) + 1)},
            )

        return await call_next(request)
