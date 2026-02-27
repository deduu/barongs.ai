from __future__ import annotations

from unittest.mock import AsyncMock

from src.core.rag.models import Document, ResultSource, SearchResult
from src.core.rag.persistent_retriever import PersistentHybridRetriever


def _doc(doc_id: str = "d1", content: str = "hello", emb: list[float] | None = None) -> Document:
    return Document(id=doc_id, content=content, embedding=emb)


class TestPersistentHybridRetriever:
    async def test_initialize_loads_and_indexes(self):
        """On startup, loads docs from PG and feeds them to the in-memory stores."""
        store = AsyncMock()
        store.load_all = AsyncMock(
            return_value=[_doc("d1", "text", emb=[0.1, 0.2])]
        )
        vector_store = AsyncMock()
        sparse_retriever = AsyncMock()
        retriever = AsyncMock()
        retriever._vector_store = vector_store
        retriever._sparse_retriever = sparse_retriever

        phr = PersistentHybridRetriever(retriever=retriever, store=store)
        await phr.initialize()

        store.initialize.assert_called_once()
        store.load_all.assert_called_once()
        # Docs with embeddings go directly to vector store (skip re-embedding)
        vector_store.upsert.assert_called_once()
        sparse_retriever.index.assert_called_once()
        loaded_docs = vector_store.upsert.call_args[0][0]
        assert len(loaded_docs) == 1
        assert loaded_docs[0].id == "d1"

    async def test_initialize_skips_empty_store(self):
        """If PG has no documents, don't call upsert/index."""
        store = AsyncMock()
        store.load_all = AsyncMock(return_value=[])
        retriever = AsyncMock()
        retriever._vector_store = AsyncMock()
        retriever._sparse_retriever = AsyncMock()

        phr = PersistentHybridRetriever(retriever=retriever, store=store)
        await phr.initialize()

        retriever._vector_store.upsert.assert_not_called()
        retriever._sparse_retriever.index.assert_not_called()

    async def test_ingest_persists_then_indexes(self):
        """Ingest delegates to HybridRetriever, then persists docs with embeddings."""
        store = AsyncMock()
        retriever = AsyncMock()

        # Simulate HybridRetriever.ingest populating embeddings
        docs = [_doc("d1", "text")]

        async def fake_ingest(documents):
            for d in documents:
                d.embedding = [0.1, 0.2]

        retriever.ingest = AsyncMock(side_effect=fake_ingest)

        phr = PersistentHybridRetriever(retriever=retriever, store=store)
        await phr.ingest(docs)

        retriever.ingest.assert_called_once_with(docs)
        store.save.assert_called_once_with(docs)

    async def test_delete_removes_from_both(self):
        """Delete removes from both HybridRetriever and PgDocumentStore."""
        store = AsyncMock()
        retriever = AsyncMock()

        phr = PersistentHybridRetriever(retriever=retriever, store=store)
        await phr.delete(["d1", "d2"])

        retriever.delete.assert_called_once_with(["d1", "d2"])
        store.delete.assert_called_once_with(["d1", "d2"])

    async def test_retrieve_delegates_to_inner(self):
        """Retrieve is pure delegation — no persistence involved."""
        store = AsyncMock()
        retriever = AsyncMock()
        expected = [
            SearchResult(
                document=_doc("d1"), score=0.9, source=ResultSource.DENSE
            )
        ]
        retriever.retrieve = AsyncMock(return_value=expected)

        phr = PersistentHybridRetriever(retriever=retriever, store=store)
        results = await phr.retrieve("query", top_k=5)

        retriever.retrieve.assert_called_once_with("query", top_k=5, filters=None)
        assert results == expected

    async def test_initialize_no_sparse_retriever(self):
        """Initialize works when there is no sparse retriever configured."""
        store = AsyncMock()
        store.load_all = AsyncMock(
            return_value=[_doc("d1", "text", emb=[0.1, 0.2])]
        )
        retriever = AsyncMock()
        retriever._vector_store = AsyncMock()
        retriever._sparse_retriever = None

        phr = PersistentHybridRetriever(retriever=retriever, store=store)
        await phr.initialize()

        retriever._vector_store.upsert.assert_called_once()

    async def test_close_delegates_to_store(self):
        store = AsyncMock()
        retriever = AsyncMock()

        phr = PersistentHybridRetriever(retriever=retriever, store=store)
        await phr.close()

        store.close.assert_called_once()
