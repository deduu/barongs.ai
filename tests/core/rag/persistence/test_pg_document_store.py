from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.rag.models import Document
from src.core.rag.persistence.pg_document_store import PgDocumentStore

# --- Helpers ---


def _make_doc(
    doc_id: str = "doc-1",
    content: str = "hello world",
    metadata: dict[str, Any] | None = None,
    embedding: list[float] | None = None,
) -> Document:
    return Document(
        id=doc_id,
        content=content,
        metadata=metadata or {},
        embedding=embedding,
    )


def _fake_pool() -> tuple[MagicMock, AsyncMock]:
    """Create a fake asyncpg connection pool. Returns (pool, conn)."""
    conn = AsyncMock()
    pool = MagicMock()

    @asynccontextmanager
    async def _acquire():
        yield conn

    pool.acquire = _acquire
    pool.close = AsyncMock()
    return pool, conn


# --- Tests ---


class TestPgDocumentStore:
    async def test_initialize_creates_table(self):
        with patch("src.core.rag.persistence.pg_document_store.asyncpg") as mock_pg:
            pool, conn = _fake_pool()
            mock_pg.create_pool = AsyncMock(return_value=pool)

            store = PgDocumentStore(database_url="postgresql://test:test@localhost/test")
            await store.initialize()

            conn.execute.assert_called_once()
            sql = conn.execute.call_args[0][0]
            assert "CREATE TABLE IF NOT EXISTS" in sql
            assert "rag_documents" in sql

    async def test_save_documents(self):
        with patch("src.core.rag.persistence.pg_document_store.asyncpg") as mock_pg:
            pool, conn = _fake_pool()
            mock_pg.create_pool = AsyncMock(return_value=pool)

            store = PgDocumentStore(database_url="postgresql://test:test@localhost/test")
            await store.initialize()

            doc = _make_doc(embedding=[0.1, 0.2, 0.3])
            await store.save([doc])

            conn.executemany.assert_called_once()
            sql = conn.executemany.call_args[0][0]
            assert "INSERT INTO rag_documents" in sql
            assert "ON CONFLICT" in sql

    async def test_save_documents_without_embeddings(self):
        with patch("src.core.rag.persistence.pg_document_store.asyncpg") as mock_pg:
            pool, conn = _fake_pool()
            mock_pg.create_pool = AsyncMock(return_value=pool)

            store = PgDocumentStore(database_url="postgresql://test:test@localhost/test")
            await store.initialize()

            doc = _make_doc(embedding=None)
            await store.save([doc])

            conn.executemany.assert_called_once()
            args = conn.executemany.call_args[0][1]
            assert args[0][3] is None  # 4th param is embedding bytes

    async def test_load_all_returns_documents(self):
        with patch("src.core.rag.persistence.pg_document_store.asyncpg") as mock_pg:
            pool, conn = _fake_pool()
            mock_pg.create_pool = AsyncMock(return_value=pool)

            store = PgDocumentStore(database_url="postgresql://test:test@localhost/test")
            await store.initialize()

            conn.fetch = AsyncMock(
                return_value=[
                    {
                        "id": "doc-1",
                        "content": "hello",
                        "metadata": json.dumps({"title": "test"}),
                        "embedding": None,
                    }
                ]
            )

            docs = await store.load_all()
            assert len(docs) == 1
            assert docs[0].id == "doc-1"
            assert docs[0].content == "hello"
            assert docs[0].metadata == {"title": "test"}
            assert docs[0].embedding is None

    async def test_load_all_restores_embeddings(self):
        with patch("src.core.rag.persistence.pg_document_store.asyncpg") as mock_pg:
            pool, conn = _fake_pool()
            mock_pg.create_pool = AsyncMock(return_value=pool)

            store = PgDocumentStore(database_url="postgresql://test:test@localhost/test")
            await store.initialize()

            import numpy as np

            emb = [0.1, 0.2, 0.3]
            emb_bytes = np.array(emb, dtype=np.float32).tobytes()

            conn.fetch = AsyncMock(
                return_value=[
                    {
                        "id": "doc-1",
                        "content": "hello",
                        "metadata": json.dumps({}),
                        "embedding": emb_bytes,
                    }
                ]
            )

            docs = await store.load_all()
            assert docs[0].embedding is not None
            assert len(docs[0].embedding) == 3
            assert abs(docs[0].embedding[0] - 0.1) < 1e-5

    async def test_delete_by_ids(self):
        with patch("src.core.rag.persistence.pg_document_store.asyncpg") as mock_pg:
            pool, conn = _fake_pool()
            mock_pg.create_pool = AsyncMock(return_value=pool)

            store = PgDocumentStore(database_url="postgresql://test:test@localhost/test")
            await store.initialize()

            await store.delete(["doc-1", "doc-2"])

            # execute is called for CREATE TABLE + DELETE
            assert conn.execute.call_count == 2
            last_call = conn.execute.call_args_list[-1]
            sql = last_call[0][0]
            assert "DELETE FROM rag_documents" in sql

    async def test_count(self):
        with patch("src.core.rag.persistence.pg_document_store.asyncpg") as mock_pg:
            pool, conn = _fake_pool()
            mock_pg.create_pool = AsyncMock(return_value=pool)

            store = PgDocumentStore(database_url="postgresql://test:test@localhost/test")
            await store.initialize()

            conn.fetchval = AsyncMock(return_value=42)
            result = await store.count()
            assert result == 42

    async def test_close(self):
        with patch("src.core.rag.persistence.pg_document_store.asyncpg") as mock_pg:
            pool, conn = _fake_pool()
            mock_pg.create_pool = AsyncMock(return_value=pool)

            store = PgDocumentStore(database_url="postgresql://test:test@localhost/test")
            await store.initialize()
            await store.close()

            pool.close.assert_called_once()
