from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt  # type: ignore[import-untyped]


class TokenError(Exception):
    """Raised when a JWT cannot be decoded or is invalid."""


def create_access_token(
    *,
    user_id: str,
    tenant_id: str,
    email: str,
    secret_key: str,
    algorithm: str = "HS256",
    expire_minutes: int = 1440,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "email": email,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)  # type: ignore[no-any-return]


def decode_access_token(
    token: str,
    *,
    secret_key: str,
    algorithm: str = "HS256",
) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Returns the full payload dict on success.
    Raises ``TokenError`` on any failure (expired, bad signature, etc.).
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, secret_key, algorithms=[algorithm]
        )
    except jwt.ExpiredSignatureError:
        raise TokenError("Token has expired") from None
    except jwt.InvalidTokenError as exc:
        raise TokenError(f"Invalid token: {exc}") from None

    if payload.get("type") != "access":
        raise TokenError("Invalid token type")

    return payload
