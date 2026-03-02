"""Tests for RedisRateLimiter — distributed token bucket via Redis."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from src.core.middleware.rate_limiter import RedisRateLimiter, TokenBucketRateLimiter


def _make_mock_redis(max_tokens: int = 5, window_seconds: int = 60) -> MagicMock:
    """Create a mock Redis client that simulates the Lua token bucket script."""
    state: dict[str, dict[str, float]] = {}

    async def fake_eval(script: str, num_keys: int, key: str, *args: str) -> list[object]:
        mt = float(args[0])  # max_tokens
        rr = float(args[1])  # refill_rate
        now = float(args[2])  # current time

        if key not in state:
            state[key] = {"tokens": mt, "last_refill": now}

        bucket = state[key]
        elapsed = max(0.0, now - bucket["last_refill"])
        bucket["tokens"] = min(mt, bucket["tokens"] + elapsed * rr)
        bucket["last_refill"] = now

        allowed = 0
        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            allowed = 1

        return [allowed, str(bucket["tokens"])]

    client = MagicMock()
    client.eval = AsyncMock(side_effect=fake_eval)
    return client


class TestRedisRateLimiter:
    async def test_allows_requests_under_limit(self):
        client = _make_mock_redis(max_tokens=5, window_seconds=60)
        limiter = RedisRateLimiter(client, max_tokens=5, window_seconds=60)
        for _ in range(5):
            assert await limiter.check("client-1") is True

    async def test_blocks_after_limit_exhausted(self):
        client = _make_mock_redis(max_tokens=2, window_seconds=60)
        limiter = RedisRateLimiter(client, max_tokens=2, window_seconds=60)
        assert await limiter.check("c1") is True
        assert await limiter.check("c1") is True
        assert await limiter.check("c1") is False

    async def test_separate_buckets_per_client(self):
        client = _make_mock_redis(max_tokens=1, window_seconds=60)
        limiter = RedisRateLimiter(client, max_tokens=1, window_seconds=60)
        assert await limiter.check("alice") is True
        assert await limiter.check("bob") is True
        assert await limiter.check("alice") is False
        assert await limiter.check("bob") is False

    async def test_get_retry_after_when_exhausted(self):
        client = _make_mock_redis(max_tokens=1, window_seconds=60)
        limiter = RedisRateLimiter(client, max_tokens=1, window_seconds=60)
        assert await limiter.check("c1") is True
        assert await limiter.check("c1") is False
        retry = await limiter.get_retry_after("c1")
        assert retry > 0

    async def test_get_retry_after_when_available(self):
        client = _make_mock_redis(max_tokens=5, window_seconds=60)
        limiter = RedisRateLimiter(client, max_tokens=5, window_seconds=60)
        retry = await limiter.get_retry_after("c1")
        assert retry == 0.0

    async def test_fallback_on_redis_error(self):
        client = MagicMock()
        client.eval = AsyncMock(side_effect=ConnectionError("Redis down"))
        limiter = RedisRateLimiter(client, max_tokens=5, window_seconds=60)
        # Should fall back to in-memory limiter, not crash
        result = await limiter.check("c1")
        assert result is True

    async def test_fallback_tracks_state(self):
        client = MagicMock()
        client.eval = AsyncMock(side_effect=ConnectionError("Redis down"))
        limiter = RedisRateLimiter(client, max_tokens=1, window_seconds=60)
        assert await limiter.check("c1") is True  # fallback allows
        assert await limiter.check("c1") is False  # fallback blocks


class TestTokenBucketGetRetryAfter:
    """Verify get_retry_after method on existing TokenBucketRateLimiter."""

    def test_retry_after_zero_when_tokens_available(self):
        limiter = TokenBucketRateLimiter(max_tokens=5, window_seconds=60)
        assert limiter.get_retry_after("c1") == 0.0

    def test_retry_after_positive_when_exhausted(self):
        limiter = TokenBucketRateLimiter(max_tokens=1, window_seconds=60)
        limiter.check("c1")  # exhaust
        limiter.check("c1")  # now blocked
        retry = limiter.get_retry_after("c1")
        assert retry > 0
