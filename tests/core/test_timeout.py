"""Tests for timeout wrapper — enforcement and error messages."""

from __future__ import annotations

import asyncio

import pytest

from src.core.middleware.timeout import TimeoutError, with_timeout


class TestWithTimeout:
    async def test_completes_within_timeout(self):
        async def fast() -> str:
            return "done"

        result = await with_timeout(fast(), timeout_seconds=1.0)
        assert result == "done"

    async def test_raises_on_timeout(self):
        async def slow() -> str:
            await asyncio.sleep(10)
            return "done"

        with pytest.raises(TimeoutError) as exc_info:
            await with_timeout(slow(), timeout_seconds=0.05, operation_name="slow_op")

        assert "slow_op" in str(exc_info.value)
        assert exc_info.value.operation == "slow_op"
        assert exc_info.value.timeout == 0.05

    async def test_default_operation_name(self):
        async def slow() -> str:
            await asyncio.sleep(10)
            return "done"

        with pytest.raises(TimeoutError) as exc_info:
            await with_timeout(slow(), timeout_seconds=0.05)

        assert "operation" in str(exc_info.value)
