from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from src.core.models.auth import AuthContext
from src.core.models.config import AppSettings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _extract_bearer(request: Request) -> str | None:
    """Extract token from ``Authorization: Bearer <token>`` header."""
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def _extract_key(request: Request, api_key: str | None) -> str:
    """Extract API key from header or bearer token, raising 401 if missing."""
    key = api_key or _extract_bearer(request)
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    return key


async def verify_api_key(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> AuthContext:
    """FastAPI dependency that extracts an API key without validation.

    Accepts either ``X-API-Key`` header or ``Authorization: Bearer`` header.
    Returns an AuthContext with tenant_id="default".
    """
    key = _extract_key(request, api_key)
    return AuthContext(tenant_id="default", api_key=key)


def create_api_key_dependency(
    settings: AppSettings,
) -> Callable[..., Coroutine[Any, Any, AuthContext]]:
    """Create a dependency that validates the API key and resolves tenant.

    When ``settings.api_keys`` is populated, looks up the key to resolve the
    tenant_id.  Otherwise falls back to single-key mode using
    ``settings.api_key`` with tenant_id="default".
    """

    async def _verify(
        request: Request,
        api_key: str | None = Security(api_key_header),
    ) -> AuthContext:
        key = _extract_key(request, api_key)

        # Multi-key mode: lookup tenant from key
        if settings.api_keys:
            tenant_id = settings.api_keys.get(key)
            if tenant_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid API key",
                )
            return AuthContext(tenant_id=tenant_id, api_key=key)

        # Single-key mode (backward compatible)
        if key != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key",
            )
        return AuthContext(tenant_id="default", api_key=key)

    return _verify
