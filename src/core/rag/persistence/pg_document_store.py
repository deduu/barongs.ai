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
    id         TEXT PRIMARY KEY,
    content    TEXT NOT NULL,
    metadata   JSONB NOT NULL DEFAULT '{}',
    embedding  BYTEA,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_UPSERT = """\
INSERT INTO rag_documents (id, content, metadata, embedding)
VALUES ($1, $2, $3::jsonb, $4)
ON CONFLICT (id) DO UPDATE SET
    content   = EXCLUDED.content,
    metadata  = EXCLUDED.metadata,
    embedding = EXCLUDED.embedding;
"""

_SELECT_ALL = "SELECT id, content, metadata, embedding FROM rag_documents ORDER BY created_at;"

_DELETE = "DELETE FROM rag_documents WHERE id = ANY($1::text[]);"

_COUNT = "SELECT COUNT(*) FROM rag_documents;"


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

    async def initialize(self) -> None:
        """Create the connection pool and ensure the table exists."""
        self._pool = await asyncpg.create_pool(dsn=self._dsn)
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_TABLE)
        logger.info("PgDocumentStore initialised (table ensured)")

    async def save(self, documents: list[Document]) -> None:
        """Upsert documents (with optional embeddings) into PostgreSQL."""
        if not documents:
            return
        assert self._pool is not None

        rows: list[tuple[str, str, str, bytes | None]] = []
        for doc in documents:
            emb_bytes: bytes | None = None
            if doc.embedding is not None and np is not None:
                emb_bytes = np.array(doc.embedding, dtype=np.float32).tobytes()
            rows.append((doc.id, doc.content, json.dumps(doc.metadata), emb_bytes))

        async with self._pool.acquire() as conn:
            await conn.executemany(_UPSERT, rows)
        logger.info("Saved %d documents to PostgreSQL", len(documents))

    async def load_all(self) -> list[Document]:
        """Load all documents from PostgreSQL, restoring embeddings."""
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            records: list[Any] = await conn.fetch(_SELECT_ALL)

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

        logger.info("Loaded %d documents from PostgreSQL", len(documents))
        return documents

    async def delete(self, ids: list[str]) -> None:
        """Delete documents by their IDs."""
        if not ids:
            return
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            await conn.execute(_DELETE, ids)
        logger.info("Deleted %d documents from PostgreSQL", len(ids))

    async def count(self) -> int:
        """Return the total number of persisted documents."""
        assert self._pool is not None

        async with self._pool.acquire() as conn:
            result: int = await conn.fetchval(_COUNT)
        return result

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
