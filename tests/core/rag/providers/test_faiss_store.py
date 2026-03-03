"""Tests for FAISS vector store."""

from __future__ import annotations

import pytest

from src.core.rag.models import Document, ResultSource
from src.core.rag.providers.vector_stores.faiss import FAISSVectorStore


@pytest.fixture
def store():
    return FAISSVectorStore(dimension=3)


@pytest.fixture
def sample_docs():
    return [
        Document(id="d1", content="Python is great", embedding=[1.0, 0.0, 0.0]),
        Document(id="d2", content="FastAPI is fast", embedding=[0.0, 1.0, 0.0]),
        Document(id="d3", content="Pydantic validates", embedding=[0.0, 0.0, 1.0]),
    ]


class TestFAISSVectorStoreProperties:
    def test_name(self, store):
        assert store.name == "faiss"


class TestFAISSUpsert:
    async def test_upsert_stores_docs(self, store, sample_docs):
        await store.upsert(sample_docs)
        docs = await store.list_documents()
        assert len(docs) == 3

    async def test_upsert_updates_existing(self, store):
        doc = Document(id="d1", content="v1", embedding=[1.0, 0.0, 0.0])
        await store.upsert([doc])
        updated = Document(id="d1", content="v2", embedding=[0.0, 1.0, 0.0])
        await store.upsert([updated])
        docs = await store.list_documents()
        assert len(docs) == 1
        assert docs[0].content == "v2"


class TestFAISSSearch:
    async def test_search_returns_results(self, store, sample_docs):
        await store.upsert(sample_docs)
        results = await store.search([1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0].document.id == "d1"
        assert results[0].source == ResultSource.DENSE

    async def test_search_respects_top_k(self, store, sample_docs):
        await store.upsert(sample_docs)
        results = await store.search([1.0, 0.0, 0.0], top_k=1)
        assert len(results) == 1

    async def test_search_empty_store(self, store):
        results = await store.search([1.0, 0.0, 0.0])
        assert results == []

    async def test_scores_sorted_descending(self, store, sample_docs):
        await store.upsert(sample_docs)
        results = await store.search([1.0, 0.0, 0.0], top_k=3)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestFAISSDelete:
    async def test_delete_removes_document(self, store, sample_docs):
        await store.upsert(sample_docs)
        await store.delete(["d1"])
        docs = await store.list_documents()
        assert len(docs) == 2
        assert all(d.id != "d1" for d in docs)

    async def test_delete_nonexistent_is_noop(self, store, sample_docs):
        await store.upsert(sample_docs)
        await store.delete(["nonexistent"])
        docs = await store.list_documents()
        assert len(docs) == 3


class TestFAISSListDocuments:
    async def test_list_with_limit(self, store, sample_docs):
        await store.upsert(sample_docs)
        docs = await store.list_documents(limit=2)
        assert len(docs) == 2

    async def test_list_with_offset(self, store, sample_docs):
        await store.upsert(sample_docs)
        all_docs = await store.list_documents()
        offset_docs = await store.list_documents(offset=1)
        assert len(offset_docs) == len(all_docs) - 1

    async def test_list_with_metadata_filter(self, store):
        docs = [
            Document(
                id="a1",
                content="user A doc",
                metadata={"user_id": "alice"},
                embedding=[1.0, 0.0, 0.0],
            ),
            Document(
                id="b1",
                content="user B doc",
                metadata={"user_id": "bob"},
                embedding=[0.0, 1.0, 0.0],
            ),
            Document(
                id="a2",
                content="user A doc 2",
                metadata={"user_id": "alice"},
                embedding=[0.0, 0.0, 1.0],
            ),
        ]
        await store.upsert(docs)
        result = await store.list_documents(filters={"user_id": "alice"})
        assert len(result) == 2
        assert all(d.metadata["user_id"] == "alice" for d in result)

    async def test_list_without_filter_returns_all(self, store, sample_docs):
        await store.upsert(sample_docs)
        docs = await store.list_documents()
        assert len(docs) == 3

    async def test_list_filter_with_limit_and_offset(self, store):
        docs = [
            Document(
                id=f"d{i}",
                content=f"doc {i}",
                metadata={"user_id": "alice"},
                embedding=[float(i), 0.0, 0.0],
            )
            for i in range(5)
        ]
        await store.upsert(docs)
        result = await store.list_documents(
            filters={"user_id": "alice"}, limit=2, offset=1
        )
        assert len(result) == 2
