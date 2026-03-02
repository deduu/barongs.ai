"""Tests for HttpClientPool — shared httpx client with concurrency control."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.http.client import HttpClientPool


class TestHttpClientPool:
    async def test_get_request(self):
        pool = HttpClientPool(max_connections=10, max_concurrent=5)
        with patch.object(pool._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(status_code=200, text="ok")
            resp = await pool.get("https://example.com")
            assert resp.status_code == 200
            mock_get.assert_awaited_once_with("https://example.com")
        await pool.aclose()

    async def test_post_request(self):
        pool = HttpClientPool(max_connections=10, max_concurrent=5)
        with patch.object(pool._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=201)
            resp = await pool.post("https://example.com/api", json={"key": "val"})
            assert resp.status_code == 201
            mock_post.assert_awaited_once_with("https://example.com/api", json={"key": "val"})
        await pool.aclose()

    async def test_semaphore_limits_concurrency(self):
        pool = HttpClientPool(max_connections=10, max_concurrent=2)
        active = {"count": 0, "peak": 0}

        async def slow_get(*args, **kwargs):
            active["count"] += 1
            active["peak"] = max(active["peak"], active["count"])
            await asyncio.sleep(0.05)
            active["count"] -= 1
            return MagicMock(status_code=200)

        with patch.object(pool._client, "get", new_callable=AsyncMock, side_effect=slow_get):
            tasks = [pool.get(f"https://example.com/{i}") for i in range(5)]
            await asyncio.gather(*tasks)

        # Peak concurrent calls should not exceed semaphore limit
        assert active["peak"] <= 2
        await pool.aclose()

    async def test_aclose_closes_client(self):
        pool = HttpClientPool()
        with patch.object(pool._client, "aclose", new_callable=AsyncMock) as mock_close:
            await pool.aclose()
            mock_close.assert_awaited_once()

    async def test_default_settings(self):
        pool = HttpClientPool()
        assert pool._semaphore._value == 50  # default max_concurrent
        await pool.aclose()

    async def test_custom_timeout(self):
        pool = HttpClientPool(timeout=5.0)
        assert pool._client.timeout.connect == 5.0
        await pool.aclose()
