from __future__ import annotations

from pydantic import BaseModel, Field


class AuthContext(BaseModel):
    """Resolved authentication context for a request."""

    tenant_id: str = "default"
    api_key: str = ""
    user_id: str | None = None
    scopes: list[str] = Field(default_factory=list)
    auth_method: str = "api_key"
