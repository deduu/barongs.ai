from __future__ import annotations

import asyncio
import builtins
import functools
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


class TimeoutError(asyncio.TimeoutError):
    """Raised when an agent or tool call exceeds its timeout."""

    def __init__(self, operation: str, timeout: float) -> None:
        self.operation = operation
        self.timeout = timeout
        super().__init__(f"{operation} timed out after {timeout}s")


async def with_timeout(
    coro: Awaitable[T],
    timeout_seconds: float,
    operation_name: str = "operation",
) -> T:
    """Wrap any awaitable with a timeout.

    Raises:
        TimeoutError with context about which operation timed out.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except builtins.TimeoutError:
        raise TimeoutError(operation_name, timeout_seconds) from None


def timeout_decorator(seconds: float, operation_name: str | None = None) -> Callable[..., Any]:
    """Decorator to apply timeout to an async function."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            name = operation_name or func.__qualname__
            return await with_timeout(func(*args, **kwargs), seconds, name)

        return wrapper

    return decorator
