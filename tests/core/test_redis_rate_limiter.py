"""Tests for RedisRateLimiter — distributed token bucket via Redis."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import pytest

from src.core.middleware.rate_limiter import RedisRateLimiter, TokenBucketRateLimiter


@pytest.fixture
async def redis_client():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


class TestRedisRateLimiter:
    async def test_allows_requests_under_limit(self, redis_client):
        limiter = RedisRateLimiter(redis_client, max_tokens=5, window_seconds=60)
        for _ in range(5):
            assert await limiter.check("client-1") is True

    async def test_blocks_after_limit_exhausted(self, redis_client):
        limiter = RedisRateLimiter(redis_client, max_tokens=2, window_seconds=60)
        assert await limiter.check("c1") is True
        assert await limiter.check("c1") is True
        assert await limiter.check("c1") is False

    async def test_separate_buckets_per_client(self, redis_client):
        limiter = RedisRateLimiter(redis_client, max_tokens=1, window_seconds=60)
        assert await limiter.check("alice") is True
        assert await limiter.check("bob") is True
        assert await limiter.check("alice") is False
        assert await limiter.check("bob") is False

    async def test_tokens_refill_over_time(self, redis_client):
        limiter = RedisRateLimiter(redis_client, max_tokens=2, window_seconds=2)
        # Exhaust tokens
        assert await limiter.check("c1") is True
        assert await limiter.check("c1") is True
        assert await limiter.check("c1") is False

        # Simulate time passing by patching time.time in the module under test
        with patch(
            "src.core.middleware.rate_limiter.time.time",
            return_value=time.time() + 2.0,
        ):
            assert await limiter.check("c1") is True

    async def test_get_retry_after_when_exhausted(self, redis_client):
        limiter = RedisRateLimiter(redis_client, max_tokens=1, window_seconds=60)
        assert await limiter.check("c1") is True
        assert await limiter.check("c1") is False
        retry = await limiter.get_retry_after("c1")
        assert retry > 0

    async def test_get_retry_after_when_available(self, redis_client):
        limiter = RedisRateLimiter(redis_client, max_tokens=5, window_seconds=60)
        retry = await limiter.get_retry_after("c1")
        assert retry == 0.0

    async def test_fallback_on_redis_error(self, redis_client):
        limiter = RedisRateLimiter(redis_client, max_tokens=5, window_seconds=60)
        # Force Redis to fail
        await redis_client.aclose()
        # Should fall back to in-memory limiter, not crash
        result = await limiter.check("c1")
        assert isinstance(result, bool)


class TestTokenBucketGetRetryAfter:
    """Verify get_retry_after method added to existing TokenBucketRateLimiter."""

    def test_retry_after_zero_when_tokens_available(self):
        limiter = TokenBucketRateLimiter(max_tokens=5, window_seconds=60)
        assert limiter.get_retry_after("c1") == 0.0

    def test_retry_after_positive_when_exhausted(self):
        limiter = TokenBucketRateLimiter(max_tokens=1, window_seconds=60)
        limiter.check("c1")  # exhaust
        limiter.check("c1")  # now blocked
        retry = limiter.get_retry_after("c1")
        assert retry > 0
