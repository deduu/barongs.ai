from __future__ import annotations

import json
from typing import Any

from src.core.interfaces.memory import Memory


class RedisMemory(Memory):
    """Redis-backed memory implementation.

    Stores values as JSON-serialized strings.  Supports key-pattern
    search via Redis SCAN and optional TTL on entries.

    Args:
        client: An async Redis client instance (redis.asyncio.Redis).
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    async def get(self, key: str) -> Any | None:
        raw = await self._client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        serialized = json.dumps(value)
        if ttl_seconds is not None:
            await self._client.set(key, serialized, ex=ttl_seconds)
        else:
            await self._client.set(key, serialized)

    async def delete(self, key: str) -> bool:
        count = await self._client.delete(key)
        return count > 0

    async def search(
        self, query: str, *, top_k: int = 5, namespace: str | None = None
    ) -> list[dict[str, Any]]:
        pattern = f"{namespace}:{query}" if namespace else query
        results: list[dict[str, Any]] = []
        cursor: int | str = 0

        while len(results) < top_k:
            cursor, keys = await self._client.scan(cursor=cursor, match=pattern, count=100)
            for key in keys:
                if len(results) >= top_k:
                    break
                value = await self.get(key)
                results.append({"key": key, "value": value, "score": 1.0})
            if cursor == 0:
                break

        return results[:top_k]

    async def clear(self, namespace: str | None = None) -> int:
        pattern = f"{namespace}:*" if namespace else "*"
        count = 0
        cursor: int | str = 0

        while True:
            cursor, keys = await self._client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                count += await self._client.delete(*keys)
            if cursor == 0:
                break

        return count
