from __future__ import annotations

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.core.models.config import AppSettings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """FastAPI dependency that verifies the API key from the X-API-Key header.

    Inject settings via app.state in the actual endpoint or override this
    dependency in the app factory.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    return api_key


def create_api_key_dependency(settings: AppSettings):  # type: ignore[no-untyped-def]
    """Create a dependency that validates against the configured API key."""

    async def _verify(api_key: str | None = Security(api_key_header)) -> str:
        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key",
            )
        if api_key != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key",
            )
        return api_key

    return _verify
