from __future__ import annotations

from typing import Any

from src.core.interfaces.memory import Memory


class InMemoryStorage(Memory):
    """Simple dict-backed memory for development and testing."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        return self._store.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    async def search(
        self, query: str, *, top_k: int = 5, namespace: str | None = None
    ) -> list[dict[str, Any]]:
        results = []
        for k, v in self._store.items():
            if query.lower() in str(v).lower():
                results.append({"key": k, "value": v, "score": 1.0})
        return results[:top_k]

    async def clear(self, namespace: str | None = None) -> int:
        count = len(self._store)
        self._store.clear()
        return count
