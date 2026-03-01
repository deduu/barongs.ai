"""Tests for UserRepository with mocked asyncpg."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.auth.user_repository import DuplicateEmailError, UserRepository


def _mock_pool(mock_conn: AsyncMock) -> MagicMock:
    """Create a mock asyncpg pool with a working acquire() context manager."""
    pool = MagicMock()

    @asynccontextmanager
    async def _acquire() -> Any:
        yield mock_conn

    pool.acquire = _acquire
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def repo():
    return UserRepository(database_url="postgresql://user:pass@localhost/test")


def test_dsn_strip_asyncpg_suffix():
    repo = UserRepository(database_url="postgresql+asyncpg://u:p@host/db")
    assert repo._dsn == "postgresql://u:p@host/db"


def test_ensure_pool_raises_before_init(repo):
    with pytest.raises(RuntimeError, match="not initialized"):
        repo._ensure_pool()


@pytest.mark.asyncio
async def test_initialize_creates_pool_and_table():
    repo = UserRepository(database_url="postgresql://u:p@host/db")
    mock_conn = AsyncMock()
    pool = _mock_pool(mock_conn)

    with patch("src.core.auth.user_repository.asyncpg") as mock_asyncpg:
        mock_asyncpg.create_pool = AsyncMock(return_value=pool)
        await repo.initialize()

    assert repo._pool is pool
    mock_conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_returns_dict():
    repo = UserRepository(database_url="postgresql://u:p@host/db")

    fake_row = MagicMock()
    fake_row.__iter__ = MagicMock(return_value=iter([
        ("id", "abc-123"),
        ("email", "test@example.com"),
        ("password_hash", "$2b$..."),
        ("tenant_id", "default"),
        ("is_active", True),
        ("created_at", "2024-01-01"),
        ("updated_at", "2024-01-01"),
    ]))

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=fake_row)
    repo._pool = _mock_pool(mock_conn)

    with patch("src.core.auth.user_repository.hash_password", return_value="$2b$hashed"):
        result = await repo.create_user(email="test@example.com", password="Pass1234")

    assert isinstance(result, dict)
    mock_conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_duplicate_raises():
    import asyncpg  # type: ignore[import-untyped]

    repo = UserRepository(database_url="postgresql://u:p@host/db")

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(
        side_effect=asyncpg.UniqueViolationError("")
    )
    repo._pool = _mock_pool(mock_conn)

    with patch("src.core.auth.user_repository.hash_password", return_value="$2b$hashed"), pytest.raises(DuplicateEmailError):
        await repo.create_user(email="dup@example.com", password="Pass1234")


@pytest.mark.asyncio
async def test_get_by_email_found():
    repo = UserRepository(database_url="postgresql://u:p@host/db")

    fake_row = {"id": "1", "email": "test@example.com"}
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=fake_row)
    repo._pool = _mock_pool(mock_conn)

    result = await repo.get_by_email("test@example.com")
    assert result is not None


@pytest.mark.asyncio
async def test_get_by_email_not_found():
    repo = UserRepository(database_url="postgresql://u:p@host/db")

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    repo._pool = _mock_pool(mock_conn)

    result = await repo.get_by_email("no@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_close():
    repo = UserRepository(database_url="postgresql://u:p@host/db")
    mock_conn = AsyncMock()
    pool = _mock_pool(mock_conn)
    repo._pool = pool

    await repo.close()
    pool.close.assert_called_once()
    assert repo._pool is None
