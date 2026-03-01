"""Tests for user Pydantic models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.core.models.user import TokenResponse, UserCreate, UserLogin, UserResponse


class TestUserCreate:
    def test_valid(self):
        u = UserCreate(email="test@example.com", password="MyPass123")
        assert u.email == "test@example.com"

    def test_short_password(self):
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="Ab1")

    def test_digits_only_password(self):
        with pytest.raises(ValidationError, match="letters and numbers"):
            UserCreate(email="test@example.com", password="12345678")

    def test_letters_only_password(self):
        with pytest.raises(ValidationError, match="letters and numbers"):
            UserCreate(email="test@example.com", password="abcdefgh")

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            UserCreate(email="not-an-email", password="MyPass123")


class TestUserLogin:
    def test_valid(self):
        u = UserLogin(email="test@example.com", password="anything")
        assert u.email == "test@example.com"


class TestUserResponse:
    def test_valid(self):
        u = UserResponse(
            id="uid-1",
            email="test@example.com",
            tenant_id="default",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        assert u.id == "uid-1"


class TestTokenResponse:
    def test_valid(self):
        t = TokenResponse(
            access_token="abc.def.ghi",
            user=UserResponse(
                id="uid-1",
                email="test@example.com",
                tenant_id="default",
                is_active=True,
                created_at=datetime.now(UTC),
            ),
        )
        assert t.token_type == "bearer"
        assert t.access_token == "abc.def.ghi"
