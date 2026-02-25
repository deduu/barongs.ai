from __future__ import annotations

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from src.core.models.config import AppSettings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _extract_bearer(request: Request) -> str | None:
    """Extract token from ``Authorization: Bearer <token>`` header."""
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


async def verify_api_key(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> str:
    """FastAPI dependency that verifies the API key.

    Accepts either ``X-API-Key`` header or ``Authorization: Bearer`` header.
    """
    key = api_key or _extract_bearer(request)
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    return key


def create_api_key_dependency(settings: AppSettings):  # type: ignore[no-untyped-def]
    """Create a dependency that validates against the configured API key."""

    async def _verify(
        request: Request,
        api_key: str | None = Security(api_key_header),
    ) -> str:
        key = api_key or _extract_bearer(request)
        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key",
            )
        if key != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key",
            )
        return key

    return _verify
