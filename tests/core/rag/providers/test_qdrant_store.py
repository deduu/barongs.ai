"""Tests for Qdrant vector store (mocked client)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.rag.models import Document, ResultSource


def _mock_scored_point(doc_id: str, score: float, content: str) -> MagicMock:
    point = MagicMock()
    point.id = doc_id
    point.score = score
    point.payload = {"content": content, "metadata": {}}
    return point


# Build a fake qmodels namespace so the source module never sees None.
_fake_qmodels = SimpleNamespace(
    VectorParams=MagicMock,
    Distance=SimpleNamespace(COSINE="Cosine"),
    PointStruct=lambda **kw: SimpleNamespace(**kw),
    PointIdsList=lambda **kw: SimpleNamespace(**kw),
)


@pytest.fixture
def mock_qdrant_client():
    client = AsyncMock()
    client.collection_exists = AsyncMock(return_value=True)
    client.create_collection = AsyncMock()
    client.upsert = AsyncMock()
    client.delete = AsyncMock()
    client.query_points = AsyncMock(return_value=MagicMock(points=[]))
    client.scroll = AsyncMock(return_value=([], None))
    return client


@pytest.fixture
def store(mock_qdrant_client):
    with (
        patch(
            "src.core.rag.providers.vector_stores.qdrant.AsyncQdrantClient",
            return_value=mock_qdrant_client,
        ),
        patch(
            "src.core.rag.providers.vector_stores.qdrant.qmodels",
            _fake_qmodels,
        ),
    ):
        from src.core.rag.providers.vector_stores.qdrant import QdrantVectorStore

        yield QdrantVectorStore(
            collection_name="test", url="http://localhost:6333", dimension=3
        )


class TestQdrantProperties:
    def test_name(self, store):
        assert store.name == "qdrant"


class TestQdrantUpsert:
    async def test_upsert_calls_client(self, store, mock_qdrant_client):
        docs = [Document(id="d1", content="hello", embedding=[0.1, 0.2, 0.3])]
        await store.upsert(docs)
        mock_qdrant_client.upsert.assert_called_once()

    async def test_upsert_ensures_collection(self, store, mock_qdrant_client):
        store._collection_ensured = False
        mock_qdrant_client.collection_exists = AsyncMock(return_value=False)
        docs = [Document(id="d1", content="hello", embedding=[0.1, 0.2, 0.3])]
        await store.upsert(docs)
        mock_qdrant_client.create_collection.assert_called_once()


class TestQdrantSearch:
    async def test_search_returns_results(self, store, mock_qdrant_client):
        mock_qdrant_client.query_points = AsyncMock(
            return_value=MagicMock(
                points=[_mock_scored_point("d1", 0.95, "hello")]
            )
        )
        results = await store.search([0.1, 0.2, 0.3], top_k=5)
        assert len(results) == 1
        assert results[0].document.id == "d1"
        assert results[0].score == 0.95
        assert results[0].source == ResultSource.DENSE

    async def test_search_empty(self, store, mock_qdrant_client):
        results = await store.search([0.1, 0.2, 0.3])
        assert results == []


class TestQdrantDelete:
    async def test_delete_calls_client(self, store, mock_qdrant_client):
        await store.delete(["d1", "d2"])
        mock_qdrant_client.delete.assert_called_once()


class TestQdrantListDocuments:
    async def test_list_returns_docs(self, store, mock_qdrant_client):
        point = MagicMock()
        point.id = "d1"
        point.payload = {"content": "hello", "metadata": {"source": "test"}}
        mock_qdrant_client.scroll = AsyncMock(return_value=([point], None))
        docs = await store.list_documents()
        assert len(docs) == 1
        assert docs[0].id == "d1"
        assert docs[0].content == "hello"
