from __future__ import annotations

import asyncio
from typing import Any


class PipelineSession:
    """Holds the state of a paused deep search pipeline."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._resume_event = asyncio.Event()
        self.user_response: dict[str, Any] | None = None

    async def wait_for_confirmation(self, timeout: float = 600.0) -> dict[str, Any] | None:
        """Block until user confirms/edits the outline, or timeout."""
        try:
            await asyncio.wait_for(self._resume_event.wait(), timeout=timeout)
            return self.user_response
        except TimeoutError:
            return None

    def confirm(self, response: dict[str, Any]) -> None:
        """Called by the REST endpoint when user submits their edits."""
        self.user_response = response
        self._resume_event.set()


class SessionStore:
    """In-memory session store for pipeline pause/resume.

    Can be replaced with a Redis-backed implementation for multi-worker production.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, PipelineSession] = {}

    def create(self, session_id: str) -> PipelineSession:
        session = PipelineSession(session_id)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> PipelineSession | None:
        return self._sessions.get(session_id)

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
