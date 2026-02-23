from __future__ import annotations

from fastapi import Request

from src.core.models.config import AppSettings


async def get_settings(request: Request) -> AppSettings:
    """FastAPI dependency to retrieve app settings from app state."""
    return request.app.state.settings  # type: ignore[no-any-return]
