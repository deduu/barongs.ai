"""PostgreSQL user store for email+password authentication."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import asyncpg  # type: ignore[import-untyped]

from src.core.auth.password import hash_password

logger = logging.getLogger(__name__)

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS users (
    id             TEXT PRIMARY KEY,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    tenant_id      TEXT NOT NULL DEFAULT 'default',
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_INSERT_USER = """\
INSERT INTO users (id, email, password_hash, tenant_id)
VALUES ($1, $2, $3, $4)
RETURNING id, email, password_hash, tenant_id, is_active, created_at, updated_at;
"""

_SELECT_BY_EMAIL = """\
SELECT id, email, password_hash, tenant_id, is_active, created_at, updated_at
FROM users WHERE email = $1;
"""

_SELECT_BY_ID = """\
SELECT id, email, password_hash, tenant_id, is_active, created_at, updated_at
FROM users WHERE id = $1;
"""


class DuplicateEmailError(Exception):
    """Raised when attempting to register an email that already exists."""


class UserRepository:
    """Async PostgreSQL CRUD for user accounts.

    Follows the same pool lifecycle pattern as ``PgDocumentStore``.
    """

    def __init__(self, database_url: str) -> None:
        self._dsn = database_url.replace("postgresql+asyncpg://", "postgresql://")
        self._pool: asyncpg.Pool | None = None  # type: ignore[type-arg]

    def _ensure_pool(self) -> asyncpg.Pool:  # type: ignore[type-arg]
        if self._pool is None:
            raise RuntimeError("UserRepository not initialized. Call initialize() first.")
        return self._pool

    async def initialize(self) -> None:
        """Create connection pool and ensure the users table exists."""
        self._pool = await asyncpg.create_pool(dsn=self._dsn)
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_TABLE)
        logger.info("UserRepository initialised (users table ensured)")

    async def create_user(
        self, *, email: str, password: str, tenant_id: str = "default"
    ) -> dict[str, Any]:
        """Insert a new user. Returns the row dict.

        Raises ``DuplicateEmailError`` if the email already exists.
        """
        pool = self._ensure_pool()
        user_id = str(uuid.uuid4())
        hashed = hash_password(password)

        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(_INSERT_USER, user_id, email, hashed, tenant_id)
        except asyncpg.UniqueViolationError:
            raise DuplicateEmailError(f"Email already registered: {email}") from None

        return dict(row)  # type: ignore[arg-type]

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        """Look up a user by email. Returns None if not found."""
        pool = self._ensure_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(_SELECT_BY_EMAIL, email)
        return dict(row) if row else None

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Look up a user by ID. Returns None if not found."""
        pool = self._ensure_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(_SELECT_BY_ID, user_id)
        return dict(row) if row else None

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
