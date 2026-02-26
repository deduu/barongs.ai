"""Tests for RAG ABCs — verify they cannot be instantiated directly
and that stub implementations work correctly."""

from __future__ import annotations

from typing import Any

import pytest

from src.core.rag.interfaces.embedder import Embedder
from src.core.rag.interfaces.reranker import Reranker
from src.core.rag.interfaces.sparse_retriever import SparseRetriever
from src.core.rag.interfaces.vector_store import VectorStore
from src.core.rag.models import Document, ResultSource, SearchResult

# --- Stubs ---


class _StubEmbedder(Embedder):
    @property
    def name(self) -> str:
        return "stub_embedder"

    @property
    def dimension(self) -> int:
        return 3

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3]] * len(texts)


class _StubVectorStore(VectorStore):
    def __init__(self) -> None:
        self._docs: dict[str, Document] = {}

    @property
    def name(self) -> str:
        return "stub_vector_store"

    async def upsert(self, documents: list[Document]) -> None:
        for doc in documents:
            self._docs[doc.id] = doc

    async def search(
        self,
        vector: list[float],
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        results = []
        for doc in list(self._docs.values())[:top_k]:
            results.append(
                SearchResult(document=doc, score=0.9, source=ResultSource.DENSE)
            )
        return results

    async def delete(self, ids: list[str]) -> None:
        for doc_id in ids:
            self._docs.pop(doc_id, None)


class _StubSparseRetriever(SparseRetriever):
    def __init__(self) -> None:
        self._docs: dict[str, Document] = {}

    @property
    def name(self) -> str:
        return "stub_sparse"

    async def index(self, documents: list[Document]) -> None:
        for doc in documents:
            self._docs[doc.id] = doc

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        results = []
        for doc in list(self._docs.values())[:top_k]:
            if query.lower() in doc.content.lower():
                results.append(
                    SearchResult(document=doc, score=0.8, source=ResultSource.SPARSE)
                )
        return results

    async def delete(self, ids: list[str]) -> None:
        for doc_id in ids:
            self._docs.pop(doc_id, None)


class _StubReranker(Reranker):
    @property
    def name(self) -> str:
        return "stub_reranker"

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        *,
        top_k: int = 5,
    ) -> list[SearchResult]:
        reranked = [
            SearchResult(
                document=r.document,
                score=r.score * 1.1,
                source=ResultSource.RERANKED,
            )
            for r in results[:top_k]
        ]
        return sorted(reranked, key=lambda r: r.score, reverse=True)


# --- Tests ---


class TestEmbedderABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            Embedder()  # type: ignore[abstract]

    async def test_stub_embed(self):
        embedder = _StubEmbedder()
        vectors = await embedder.embed(["hello", "world"])
        assert len(vectors) == 2
        assert len(vectors[0]) == 3

    def test_stub_name(self):
        assert _StubEmbedder().name == "stub_embedder"

    def test_stub_dimension(self):
        assert _StubEmbedder().dimension == 3


class TestVectorStoreABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            VectorStore()  # type: ignore[abstract]

    async def test_stub_upsert_and_search(self):
        store = _StubVectorStore()
        doc = Document(id="d1", content="hello", embedding=[0.1, 0.2, 0.3])
        await store.upsert([doc])
        results = await store.search([0.1, 0.2, 0.3], top_k=5)
        assert len(results) == 1
        assert results[0].document.id == "d1"
        assert results[0].source == ResultSource.DENSE

    async def test_stub_delete(self):
        store = _StubVectorStore()
        doc = Document(id="d1", content="hello", embedding=[0.1, 0.2, 0.3])
        await store.upsert([doc])
        await store.delete(["d1"])
        results = await store.search([0.1, 0.2, 0.3])
        assert len(results) == 0

    def test_stub_name(self):
        assert _StubVectorStore().name == "stub_vector_store"


class TestSparseRetrieverABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            SparseRetriever()  # type: ignore[abstract]

    async def test_stub_index_and_search(self):
        retriever = _StubSparseRetriever()
        doc = Document(id="d1", content="hello world")
        await retriever.index([doc])
        results = await retriever.search("hello")
        assert len(results) == 1
        assert results[0].source == ResultSource.SPARSE

    async def test_stub_search_no_match(self):
        retriever = _StubSparseRetriever()
        doc = Document(id="d1", content="hello world")
        await retriever.index([doc])
        results = await retriever.search("xyz")
        assert len(results) == 0

    async def test_stub_delete(self):
        retriever = _StubSparseRetriever()
        doc = Document(id="d1", content="hello world")
        await retriever.index([doc])
        await retriever.delete(["d1"])
        results = await retriever.search("hello")
        assert len(results) == 0

    def test_stub_name(self):
        assert _StubSparseRetriever().name == "stub_sparse"


class TestRerankerABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            Reranker()  # type: ignore[abstract]

    async def test_stub_rerank(self):
        reranker = _StubReranker()
        doc = Document(id="d1", content="hello")
        results = [SearchResult(document=doc, score=0.8, source=ResultSource.DENSE)]
        reranked = await reranker.rerank("hello", results, top_k=5)
        assert len(reranked) == 1
        assert reranked[0].source == ResultSource.RERANKED
        assert reranked[0].score > 0.8

    async def test_stub_rerank_respects_top_k(self):
        reranker = _StubReranker()
        docs = [Document(id=f"d{i}", content=f"text {i}") for i in range(5)]
        results = [
            SearchResult(document=d, score=0.5 + i * 0.1, source=ResultSource.DENSE)
            for i, d in enumerate(docs)
        ]
        reranked = await reranker.rerank("text", results, top_k=2)
        assert len(reranked) == 2

    def test_stub_name(self):
        assert _StubReranker().name == "stub_reranker"
