from __future__ import annotations

from typing import Any

from src.core.interfaces.memory import Memory


class ConversationMemory(Memory):
    """Sliding-window conversation memory.

    Stores chat messages per session_id, keeping only the most recent
    `window_size` messages. Used for short-term memory recall.

    Usage:
        mem = ConversationMemory(window_size=20)
        await mem.set("session_123", {"role": "user", "content": "Hello"})
        history = await mem.get("session_123")  # list of messages
    """

    def __init__(self, window_size: int = 20) -> None:
        self._window_size = window_size
        self._sessions: dict[str, list[dict[str, Any]]] = {}

    async def get(self, key: str) -> Any | None:
        """Get conversation history for a session. Returns list of messages or None."""
        messages = self._sessions.get(key)
        if messages is None:
            return None
        return list(messages)

    async def set(
        self, key: str, value: Any, ttl_seconds: int | None = None, **kwargs: Any
    ) -> None:
        """Append a message to a session's conversation history.

        Args:
            key: Session ID.
            value: Message dict with 'role' and 'content'.
            ttl_seconds: Ignored (sliding window handles eviction).
        """
        if key not in self._sessions:
            self._sessions[key] = []
        self._sessions[key].append(value)
        # Enforce sliding window
        if len(self._sessions[key]) > self._window_size:
            self._sessions[key] = self._sessions[key][-self._window_size :]

    async def delete(self, key: str) -> bool:
        """Delete an entire session's history."""
        return self._sessions.pop(key, None) is not None

    async def search(
        self, query: str, *, top_k: int = 5, namespace: str | None = None
    ) -> list[dict[str, Any]]:
        """Search across all sessions for messages matching the query."""
        results: list[dict[str, Any]] = []
        for session_id, messages in self._sessions.items():
            for msg in messages:
                if query.lower() in str(msg).lower():
                    results.append({"key": session_id, "value": msg, "score": 1.0})
        return results[:top_k]

    async def clear(self, namespace: str | None = None) -> int:
        """Clear all sessions."""
        count = len(self._sessions)
        self._sessions.clear()
        return count
