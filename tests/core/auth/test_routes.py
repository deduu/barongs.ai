"""Integration tests for auth routes using FastAPI TestClient."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.auth.routes import create_auth_router
from src.core.auth.user_repository import DuplicateEmailError, UserRepository
from src.core.models.config import AppSettings


def _make_user_row(
    user_id: str = "uid-1",
    email: str = "test@example.com",
    password_hash: str = "$2b$12$hashed",
    tenant_id: str = "default",
    is_active: bool = True,
) -> dict:
    return {
        "id": user_id,
        "email": email,
        "password_hash": password_hash,
        "tenant_id": tenant_id,
        "is_active": is_active,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }


@pytest.fixture
def settings():
    return AppSettings(
        jwt_secret_key="test-jwt-secret",
        user_auth_enabled=True,
        environment="development",
    )


@pytest.fixture
def user_repo():
    repo = AsyncMock(spec=UserRepository)
    return repo


@pytest.fixture
def client(settings, user_repo):
    app = FastAPI()
    app.include_router(create_auth_router(settings, user_repo))
    return TestClient(app)


def test_register_success(client, user_repo):
    user_repo.create_user = AsyncMock(return_value=_make_user_row())

    resp = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "MyPass123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test@example.com"


def test_register_duplicate_email(client, user_repo):
    user_repo.create_user = AsyncMock(side_effect=DuplicateEmailError("dup"))

    resp = client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "MyPass123"},
    )
    assert resp.status_code == 409


def test_register_weak_password(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "short"},
    )
    assert resp.status_code == 422  # Pydantic validation


def test_login_success(client, user_repo):
    row = _make_user_row()
    user_repo.get_by_email = AsyncMock(return_value=row)

    with patch("src.core.auth.routes.verify_password", return_value=True):
        resp = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "MyPass123"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test@example.com"


def test_login_wrong_password(client, user_repo):
    row = _make_user_row()
    user_repo.get_by_email = AsyncMock(return_value=row)

    with patch("src.core.auth.routes.verify_password", return_value=False):
        resp = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
        )
    assert resp.status_code == 401


def test_login_unknown_email(client, user_repo):
    user_repo.get_by_email = AsyncMock(return_value=None)

    resp = client.post(
        "/api/auth/login",
        json={"email": "unknown@example.com", "password": "MyPass123"},
    )
    assert resp.status_code == 401


def test_login_disabled_account(client, user_repo):
    row = _make_user_row(is_active=False)
    user_repo.get_by_email = AsyncMock(return_value=row)

    with patch("src.core.auth.routes.verify_password", return_value=True):
        resp = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "MyPass123"},
        )
    assert resp.status_code == 403


def test_me_valid_token(client, user_repo, settings):
    from src.core.auth.jwt import create_access_token

    token = create_access_token(
        user_id="uid-1",
        tenant_id="default",
        email="test@example.com",
        secret_key=settings.jwt_secret_key,
    )
    user_repo.get_by_id = AsyncMock(return_value=_make_user_row())

    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


def test_me_no_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_invalid_token(client):
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401
