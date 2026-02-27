"""Persistence-aware wrapper around HybridRetriever."""

from __future__ import annotations

import logging
from typing import Any

from src.core.rag.models import Document, SearchResult
from src.core.rag.persistence.pg_document_store import PgDocumentStore
from src.core.rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)


class PersistentHybridRetriever:
    """Decorator that adds PostgreSQL persistence to ``HybridRetriever``.

    On **ingest**, documents are first indexed in-memory (FAISS + BM25)
    via the inner ``HybridRetriever``, then persisted to PostgreSQL
    together with their computed embeddings.

    On **startup** (``initialize``), all documents are loaded from
    PostgreSQL and fed directly to the vector store and sparse retriever,
    bypassing re-embedding.

    On **retrieve** and **delete**, calls are delegated transparently.
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        store: PgDocumentStore,
    ) -> None:
        self._retriever = retriever
        self._store = store
        # Expose inner stores so rag_routes can access _vector_store directly
        self._vector_store = retriever._vector_store
        self._sparse_retriever = retriever._sparse_retriever

    async def initialize(self) -> None:
        """Connect to PG, create table, and rebuild in-memory indices."""
        await self._store.initialize()

        documents = await self._store.load_all()
        if not documents:
            logger.info("No persisted documents found; starting with empty index")
            return

        # Feed pre-embedded docs directly to stores (skip re-embedding)
        await self._retriever._vector_store.upsert(documents)
        if self._retriever._sparse_retriever is not None:
            await self._retriever._sparse_retriever.index(documents)

        logger.info("Rebuilt in-memory indices from %d persisted documents", len(documents))

    async def ingest(self, documents: list[Document]) -> None:
        """Index in-memory (computes embeddings), then persist to PG."""
        await self._retriever.ingest(documents)
        await self._store.save(documents)

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Pure delegation to the inner retriever."""
        return await self._retriever.retrieve(query, top_k=top_k, filters=filters)

    async def delete(self, ids: list[str]) -> None:
        """Delete from both in-memory indices and PostgreSQL."""
        await self._retriever.delete(ids)
        await self._store.delete(ids)

    async def close(self) -> None:
        """Close the PG connection pool."""
        await self._store.close()
