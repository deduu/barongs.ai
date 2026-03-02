from __future__ import annotations

import asyncio
from typing import Any

import httpx


class HttpClientPool:
    """Application-scoped HTTP client with connection pooling and concurrency control.

    Wraps ``httpx.AsyncClient`` with a semaphore to cap the maximum number of
    concurrent outbound requests.  Create once at startup, share across all
    tools, and call ``aclose()`` during shutdown.
    """

    def __init__(
        self,
        *,
        max_connections: int = 100,
        max_keepalive: int = 20,
        max_concurrent: int = 50,
        timeout: float = 15.0,
    ) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive,
            ),
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        )

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        async with self._semaphore:
            return await self._client.get(url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        async with self._semaphore:
            return await self._client.post(url, **kwargs)

    async def aclose(self) -> None:
        await self._client.aclose()
