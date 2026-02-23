from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.models.config import AppSettings

bearer_scheme = HTTPBearer(auto_error=False)


async def _no_auth() -> str:
    """No-op dependency used when auth is disabled."""
    return ""


def create_bearer_auth_dependency(settings: AppSettings) -> Any:
    """Create a dependency that validates Bearer tokens against settings.api_key.

    Open WebUI sends ``Authorization: Bearer <key>``.  This validates that the
    token matches the configured API key.  When ``settings.openai_auth_enabled``
    is ``False``, returns a no-op dependency that accepts all requests.
    """
    if not settings.openai_auth_enabled:
        return _no_auth

    async def _verify(
        credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),  # noqa: B008
    ) -> str:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "message": "Missing authorization header",
                        "type": "auth_error",
                        "code": "missing_auth",
                    }
                },
            )
        if credentials.credentials != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "message": "Invalid API key",
                        "type": "auth_error",
                        "code": "invalid_api_key",
                    }
                },
            )
        return credentials.credentials

    return _verify
