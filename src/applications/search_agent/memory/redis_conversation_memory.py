from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from src.core.interfaces.memory import Memory

_KEY_PREFIX = "bgs:session:"


class RedisConversationMemory(Memory):
    """Redis-backed sliding-window conversation memory.

    Uses Redis Lists for atomic append-and-trim semantics:
    - ``RPUSH`` to append a message
    - ``LTRIM`` to enforce the sliding window
    - ``LRANGE`` to read the full history

    Keys are namespaced as ``bgs:session:{session_id}``.

    Args:
        client: An async Redis client instance (``redis.asyncio.Redis``).
        window_size: Maximum number of messages to keep per session.
        session_ttl_seconds: Optional TTL applied on each write.
            The timer resets every time a message is appended.
    """

    def __init__(
        self,
        client: Redis,  # type: ignore[type-arg]
        window_size: int = 20,
        session_ttl_seconds: int | None = None,
    ) -> None:
        self._client = client
        self._window_size = window_size
        self._ttl = session_ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"{_KEY_PREFIX}{session_id}"

    async def get(self, key: str) -> Any | None:
        """Get conversation history for a session. Returns list of messages or None."""
        rkey = self._key(key)
        length = await self._client.llen(rkey)
        if length == 0:
            return None
        raw_items: list[Any] = await self._client.lrange(rkey, 0, -1)
        return [json.loads(item) for item in raw_items]

    async def set(
        self, key: str, value: Any, ttl_seconds: int | None = None, **kwargs: Any
    ) -> None:
        """Append a message to a session's conversation history.

        Args:
            key: Session ID.
            value: Message dict with 'role' and 'content'.
            ttl_seconds: Ignored (uses instance-level ``session_ttl_seconds``).
        """
        rkey = self._key(key)
        await self._client.rpush(rkey, json.dumps(value))
        # Enforce sliding window: keep only the last window_size items
        await self._client.ltrim(rkey, -self._window_size, -1)
        # Refresh TTL if configured
        if self._ttl is not None:
            await self._client.expire(rkey, self._ttl)

    async def delete(self, key: str) -> bool:
        """Delete an entire session's history."""
        rkey = self._key(key)
        count = await self._client.delete(rkey)
        return count > 0

    async def search(
        self, query: str, *, top_k: int = 5, namespace: str | None = None
    ) -> list[dict[str, Any]]:
        """Search across all sessions for messages matching the query."""
        results: list[dict[str, Any]] = []
        cursor: int | str = 0
        query_lower = query.lower()

        while True:
            cursor, keys = await self._client.scan(
                cursor=cursor, match=f"{_KEY_PREFIX}*", count=100
            )
            for rkey in keys:
                if len(results) >= top_k:
                    break
                # Extract session_id from key
                session_id = rkey.removeprefix(_KEY_PREFIX) if isinstance(rkey, str) else rkey.decode().removeprefix(_KEY_PREFIX)
                raw_items: list[Any] = await self._client.lrange(rkey, 0, -1)
                for raw in raw_items:
                    if len(results) >= top_k:
                        break
                    msg = json.loads(raw)
                    if query_lower in str(msg).lower():
                        results.append({"key": session_id, "value": msg, "score": 1.0})
            if cursor == 0:
                break

        return results[:top_k]

    async def clear(self, namespace: str | None = None) -> int:
        """Clear all sessions."""
        count = 0
        cursor: int | str = 0

        while True:
            cursor, keys = await self._client.scan(
                cursor=cursor, match=f"{_KEY_PREFIX}*", count=100
            )
            if keys:
                count += await self._client.delete(*keys)
            if cursor == 0:
                break

        return count
