from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Memory(ABC):
    """Abstract interface for agent memory backends.

    Implementations might use Redis, PostgreSQL, Qdrant, or simple dicts.
    All operations are async to support networked backends.
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Retrieve a value by key. Returns None if not found."""
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Store a value. Optional TTL for expiration."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if the key existed."""
        ...

    @abstractmethod
    async def search(
        self, query: str, *, top_k: int = 5, namespace: str | None = None
    ) -> list[dict[str, Any]]:
        """Semantic or keyword search across stored memories.

        Args:
            query: The search query string.
            top_k: Maximum number of results.
            namespace: Optional scope to search within.

        Returns:
            List of dicts with at least 'key', 'value', and 'score' fields.
        """
        ...

    async def clear(self, namespace: str | None = None) -> int:
        """Clear all entries (optionally within a namespace).
        Returns number of entries cleared."""
        raise NotImplementedError
