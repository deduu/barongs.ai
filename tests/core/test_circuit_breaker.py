"""Tests for circuit breaker — state transitions and behavior."""

from __future__ import annotations

import pytest

from src.core.middleware.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
)


class TestCircuitBreaker:
    async def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    async def test_successful_call(self):
        cb = CircuitBreaker()

        async def ok() -> str:
            return "success"

        result = await cb.call(ok)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED

    async def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)

        async def fail() -> str:
            raise ValueError("boom")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(fail)

        assert cb.state == CircuitState.OPEN

    async def test_rejects_when_open(self):
        cb = CircuitBreaker(failure_threshold=1)

        async def fail() -> str:
            raise ValueError("boom")

        with pytest.raises(ValueError):
            await cb.call(fail)

        with pytest.raises(CircuitBreakerError):
            await cb.call(fail)

    async def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0)

        async def fail() -> str:
            raise ValueError("boom")

        with pytest.raises(ValueError):
            await cb.call(fail)

        # With 0.0 recovery timeout, should immediately go half-open
        assert cb.state == CircuitState.HALF_OPEN

    async def test_closes_on_success_after_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0)

        async def fail() -> str:
            raise ValueError("boom")

        async def ok() -> str:
            return "recovered"

        with pytest.raises(ValueError):
            await cb.call(fail)

        # Half-open now, next success should close it
        result = await cb.call(ok)
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED

    async def test_failure_count_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=3)

        async def fail() -> str:
            raise ValueError("boom")

        async def ok() -> str:
            return "ok"

        # 2 failures, then success
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(fail)

        await cb.call(ok)
        assert cb.state == CircuitState.CLOSED

        # Should need 3 more failures to open
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(fail)
        assert cb.state == CircuitState.CLOSED
