from __future__ import annotations

from typing import Any

from src.core.interfaces.memory import Memory


class SemanticMemory(Memory):
    """Long-term user fact storage with keyword-based search.

    Stores key-value facts with optional namespace tagging.
    Uses simple keyword matching for v1 — upgradeable to vector search later.

    Usage:
        mem = SemanticMemory()
        await mem.set("pref:lang", "User prefers Python", namespace="preferences")
        results = await mem.search("Python", namespace="preferences")
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._namespaces: dict[str, str] = {}  # key -> namespace

    async def get(self, key: str) -> Any | None:
        """Retrieve a fact by key."""
        return self._store.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
        *,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Store a fact with optional namespace."""
        self._store[key] = value
        if namespace:
            self._namespaces[key] = namespace

    async def delete(self, key: str) -> bool:
        """Delete a fact by key."""
        existed = key in self._store
        self._store.pop(key, None)
        self._namespaces.pop(key, None)
        return existed

    async def search(
        self, query: str, *, top_k: int = 5, namespace: str | None = None
    ) -> list[dict[str, Any]]:
        """Search facts by keyword matching, optionally filtered by namespace."""
        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        for key, value in self._store.items():
            # Filter by namespace if specified
            if namespace and self._namespaces.get(key) != namespace:
                continue

            # Keyword matching on both key and value
            if query_lower in str(value).lower() or query_lower in key.lower():
                score = self._compute_score(query_lower, str(value).lower(), key.lower())
                results.append({"key": key, "value": value, "score": score})

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    async def clear(self, namespace: str | None = None) -> int:
        """Clear facts, optionally filtered by namespace."""
        if namespace is None:
            count = len(self._store)
            self._store.clear()
            self._namespaces.clear()
            return count

        keys_to_remove = [k for k, ns in self._namespaces.items() if ns == namespace]
        for key in keys_to_remove:
            self._store.pop(key, None)
            self._namespaces.pop(key, None)
        return len(keys_to_remove)

    @staticmethod
    def _compute_score(query: str, value: str, key: str) -> float:
        """Simple relevance score based on keyword frequency."""
        score = 0.0
        query_words = query.split()
        for word in query_words:
            if word in value:
                score += 1.0
            if word in key:
                score += 0.5
        return score
