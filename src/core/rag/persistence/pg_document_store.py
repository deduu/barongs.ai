"""PostgreSQL document store for RAG persistence."""

from __future__ import annotations

import json
import logging
from typing import Any

import asyncpg  # type: ignore[import-untyped]

from src.core.rag.models import Document

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS rag_documents (
    id         TEXT NOT NULL,
    tenant_id  TEXT NOT NULL DEFAULT 'default',
    user_id    TEXT,
    content    TEXT NOT NULL,
    metadata   JSONB NOT NULL DEFAULT '{}',
    embedding  BYTEA,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, id)
);
"""

_MIGRATE_TENANT_COLUMN = """\
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'rag_documents' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE rag_documents ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default';
        ALTER TABLE rag_documents DROP CONSTRAINT IF EXISTS rag_documents_pkey;
        ALTER TABLE rag_documents ADD PRIMARY KEY (tenant_id, id);
    END IF;
END $$;
"""

_MIGRATE_USER_COLUMN = """\
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'rag_documents' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE rag_documents ADD COLUMN user_id TEXT;
    END IF;
END $$;
"""

_UPSERT = """\
INSERT INTO rag_documents (id, tenant_id, user_id, content, metadata, embedding)
VALUES ($1, $2, $3, $4, $5::jsonb, $6)
ON CONFLICT (tenant_id, id) DO UPDATE SET
    user_id   = EXCLUDED.user_id,
    content   = EXCLUDED.content,
    metadata  = EXCLUDED.metadata,
    embedding = EXCLUDED.embedding;
"""

_SELECT_ALL = """\
SELECT id, content, metadata, embedding FROM rag_documents
WHERE tenant_id = $1 ORDER BY created_at;
"""

_DELETE = "DELETE FROM rag_documents WHERE tenant_id = $1 AND id = ANY($2::text[]);"

_SELECT_ALL_TENANTS = """\
SELECT id, content, metadata, embedding FROM rag_documents ORDER BY created_at;
"""

_COUNT = "SELECT COUNT(*) FROM rag_documents WHERE tenant_id = $1;"


class PgDocumentStore:
    """PostgreSQL-backed document store for RAG persistence.

    Stores document content, metadata (as JSONB), and pre-computed
    embeddings (as BYTEA-serialised numpy float32 arrays).  On startup
    the full document set can be loaded back to rebuild in-memory
    indices (FAISS, BM25) without re-calling the embedding API.

    Args:
        database_url: asyncpg-compatible connection string
            (e.g. ``postgresql://user:pass@host:5432/db``).
    """

    def __init__(self, database_url: str) -> None:
        # asyncpg does not understand the +asyncpg driver suffix
        self._dsn = database_url.replace("postgresql+asyncpg://", "postgresql://")
        self._pool: asyncpg.Pool | None = None  # type: ignore[type-arg]

    def _ensure_pool(self) -> asyncpg.Pool:  # type: ignore[type-arg]
        """Return the pool, raising RuntimeError if not initialized."""
        if self._pool is None:
            raise RuntimeError("PgDocumentStore not initialized. Call initialize() first.")
        return self._pool

    async def initialize(self) -> None:
        """Create the connection pool and ensure the table exists."""
        self._pool = await asyncpg.create_pool(dsn=self._dsn, min_size=2, max_size=5)
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_TABLE)
            await conn.execute(_MIGRATE_TENANT_COLUMN)
            await conn.execute(_MIGRATE_USER_COLUMN)
        logger.info("PgDocumentStore initialised (table ensured)")

    async def save(
        self,
        documents: list[Document],
        *,
        tenant_id: str = "default",
        user_id: str | None = None,
    ) -> None:
        """Upsert documents (with optional embeddings) into PostgreSQL."""
        if not documents:
            return
        pool = self._ensure_pool()

        rows: list[tuple[str, str, str | None, str, str, bytes | None]] = []
        for doc in documents:
            emb_bytes: bytes | None = None
            if doc.embedding is not None and np is not None:
                emb_bytes = np.array(doc.embedding, dtype=np.float32).tobytes()
            doc_user_id = user_id or doc.metadata.get("user_id")
            rows.append(
                (doc.id, tenant_id, doc_user_id, doc.content, json.dumps(doc.metadata), emb_bytes)
            )

        async with pool.acquire() as conn:
            await conn.executemany(_UPSERT, rows)
        logger.info("Saved %d documents to PostgreSQL (tenant=%s)", len(documents), tenant_id)

    async def load_all(self, *, tenant_id: str = "default") -> list[Document]:
        """Load all documents for a tenant from PostgreSQL, restoring embeddings."""
        pool = self._ensure_pool()

        async with pool.acquire() as conn:
            records: list[Any] = await conn.fetch(_SELECT_ALL, tenant_id)

        documents: list[Document] = []
        for row in records:
            embedding: list[float] | None = None
            if row["embedding"] is not None and np is not None:
                embedding = np.frombuffer(row["embedding"], dtype=np.float32).tolist()

            metadata = row["metadata"]
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            documents.append(
                Document(
                    id=row["id"],
                    content=row["content"],
                    metadata=metadata,
                    embedding=embedding,
                )
            )

        logger.info("Loaded %d documents from PostgreSQL (tenant=%s)", len(documents), tenant_id)
        return documents

    async def load_all_tenants(self) -> list[Document]:
        """Load all documents across all tenants (used for startup index rebuild)."""
        pool = self._ensure_pool()

        async with pool.acquire() as conn:
            records: list[Any] = await conn.fetch(_SELECT_ALL_TENANTS)

        documents: list[Document] = []
        for row in records:
            embedding: list[float] | None = None
            if row["embedding"] is not None and np is not None:
                embedding = np.frombuffer(row["embedding"], dtype=np.float32).tolist()

            metadata = row["metadata"]
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            documents.append(
                Document(
                    id=row["id"],
                    content=row["content"],
                    metadata=metadata,
                    embedding=embedding,
                )
            )

        logger.info("Loaded %d documents from PostgreSQL (all tenants)", len(documents))
        return documents

    async def delete(self, ids: list[str], *, tenant_id: str = "default") -> None:
        """Delete documents by their IDs within a tenant."""
        if not ids:
            return
        pool = self._ensure_pool()

        async with pool.acquire() as conn:
            await conn.execute(_DELETE, tenant_id, ids)
        logger.info("Deleted %d documents from PostgreSQL (tenant=%s)", len(ids), tenant_id)

    async def count(self, *, tenant_id: str = "default") -> int:
        """Return the total number of persisted documents for a tenant."""
        pool = self._ensure_pool()

        async with pool.acquire() as conn:
            result: int = await conn.fetchval(_COUNT, tenant_id)
        return result

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
