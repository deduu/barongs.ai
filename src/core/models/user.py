from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Registration input."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if v.isdigit() or v.isalpha():
            raise ValueError("Password must contain both letters and numbers")
        return v


class UserLogin(BaseModel):
    """Login input."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public user representation (no password hash)."""

    id: str
    email: str
    tenant_id: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT response returned on login/register."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
