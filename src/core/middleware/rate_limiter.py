from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

_LUA_TOKEN_BUCKET = """\
local key = KEYS[1]
local max_tokens = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

if tokens == nil then
    tokens = max_tokens
    last_refill = now
end

local elapsed = math.max(0, now - last_refill)
tokens = math.min(max_tokens, tokens + elapsed * refill_rate)
last_refill = now

local allowed = 0
if tokens >= 1 then
    tokens = tokens - 1
    allowed = 1
end

redis.call('HMSET', key, 'tokens', tostring(tokens), 'last_refill', tostring(last_refill))
redis.call('EXPIRE', key, ttl)

return {allowed, tostring(tokens)}
"""


class RateLimitExceededError(Exception):
    """Raised when the rate limit is exceeded."""

    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after:.1f}s")


class TokenBucketRateLimiter:
    """In-memory token bucket rate limiter.

    Each client_id gets its own bucket with `max_tokens` capacity.
    Tokens refill at a rate of `max_tokens / window_seconds` per second.
    """

    def __init__(self, max_tokens: int = 100, window_seconds: int = 60) -> None:
        self._max_tokens = max_tokens
        self._refill_rate = max_tokens / window_seconds
        self._buckets: dict[str, float] = defaultdict(lambda: float(max_tokens))
        self._last_refill: dict[str, float] = {}

    def check(self, client_id: str) -> bool:
        """Check if a request is allowed. Consumes one token if allowed."""
        self._refill(client_id)
        if self._buckets[client_id] >= 1.0:
            self._buckets[client_id] -= 1.0
            return True
        return False

    def check_or_raise(self, client_id: str) -> None:
        """Check rate limit, raising RateLimitExceeded if exceeded."""
        if not self.check(client_id):
            retry_after = self.get_retry_after(client_id)
            raise RateLimitExceededError(retry_after)

    def get_retry_after(self, client_id: str) -> float:
        """Seconds until at least one token is available."""
        self._refill(client_id)
        if self._buckets[client_id] >= 1.0:
            return 0.0
        tokens_needed = 1.0 - self._buckets[client_id]
        return tokens_needed / self._refill_rate

    def _refill(self, client_id: str) -> None:
        now = time.monotonic()
        last = self._last_refill.get(client_id, now)
        elapsed = now - last
        self._last_refill[client_id] = now

        self._buckets[client_id] = min(
            self._max_tokens,
            self._buckets[client_id] + elapsed * self._refill_rate,
        )


class RedisRateLimiter:
    """Redis-backed distributed token bucket rate limiter.

    Uses an atomic Lua script so the check-and-consume is a single
    Redis round-trip, safe across multiple replicas.
    Falls back to an in-memory ``TokenBucketRateLimiter`` if Redis is
    unreachable.
    """

    _KEY_PREFIX = "bgs:rl:"

    def __init__(
        self,
        client: Any,
        max_tokens: int = 100,
        window_seconds: int = 60,
    ) -> None:
        self._client = client
        self._max_tokens = max_tokens
        self._window_seconds = window_seconds
        self._refill_rate = max_tokens / window_seconds
        self._fallback = TokenBucketRateLimiter(max_tokens, window_seconds)

    async def _run_lua(self, client_id: str) -> tuple[bool, float]:
        """Execute Lua script, return (allowed, remaining_tokens)."""
        result = await self._client.eval(
            _LUA_TOKEN_BUCKET,
            1,
            f"{self._KEY_PREFIX}{client_id}",
            str(self._max_tokens),
            str(self._refill_rate),
            str(time.time()),
            str(self._window_seconds * 2),
        )
        allowed = bool(int(result[0]))
        remaining = float(result[1])
        return allowed, remaining

    async def check(self, client_id: str) -> bool:
        """Check if request is allowed. Atomic across all replicas."""
        try:
            allowed, _ = await self._run_lua(client_id)
            return allowed
        except Exception:
            logger.warning("Redis rate limiter failed, falling back to in-memory")
            return self._fallback.check(client_id)

    async def get_retry_after(self, client_id: str) -> float:
        """Seconds until at least one token is available."""
        try:
            _, remaining = await self._run_lua(client_id)
            if remaining >= 1.0:
                return 0.0
            tokens_needed = 1.0 - remaining
            return tokens_needed / self._refill_rate
        except Exception:
            return self._fallback.get_retry_after(client_id)
