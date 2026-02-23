from __future__ import annotations

import time
from collections import defaultdict


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
            tokens_needed = 1.0 - self._buckets[client_id]
            retry_after = tokens_needed / self._refill_rate
            raise RateLimitExceededError(retry_after)

    def _refill(self, client_id: str) -> None:
        now = time.monotonic()
        last = self._last_refill.get(client_id, now)
        elapsed = now - last
        self._last_refill[client_id] = now

        self._buckets[client_id] = min(
            self._max_tokens,
            self._buckets[client_id] + elapsed * self._refill_rate,
        )
