from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any, TypeVar

T = TypeVar("T")


async def gather_with_timeout(
    *coros: Awaitable[T],
    timeout_seconds: float = 30.0,
    return_exceptions: bool = False,
) -> list[T | BaseException]:
    """Run multiple coroutines concurrently with a shared timeout.

    Args:
        *coros: Coroutines to run.
        timeout_seconds: Maximum time for all coroutines combined.
        return_exceptions: If True, exceptions are returned instead of raised.

    Returns:
        List of results (or exceptions if return_exceptions=True).
    """
    return await asyncio.wait_for(
        asyncio.gather(*coros, return_exceptions=return_exceptions),
        timeout=timeout_seconds,
    )


async def retry_async(
    func: Any,
    *args: Any,
    max_retries: int = 3,
    delay_seconds: float = 1.0,
    backoff_factor: float = 2.0,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    **kwargs: Any,
) -> Any:
    """Retry an async function with exponential backoff.

    Args:
        func: The async function to call.
        *args: Positional arguments for func.
        max_retries: Maximum number of retry attempts.
        delay_seconds: Initial delay between retries.
        backoff_factor: Multiplier for delay after each retry.
        retry_exceptions: Exception types that trigger a retry.
        **kwargs: Keyword arguments for func.

    Returns:
        The result of func(*args, **kwargs).

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retry_exceptions as exc:
            last_exception = exc
            if attempt < max_retries:
                await asyncio.sleep(delay_seconds * (backoff_factor**attempt))

    raise last_exception  # type: ignore[misc]
