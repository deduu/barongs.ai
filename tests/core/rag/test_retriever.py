"""Tests for HybridRetriever — the composite retrieval pipeline."""

from __future__ import annotations

from typing import Any

import pytest

from src.core.rag.interfaces.embedder import Embedder
from src.core.rag.interfaces.reranker import Reranker
from src.core.rag.interfaces.sparse_retriever import SparseRetriever
from src.core.rag.interfaces.vector_store import VectorStore
from src.core.rag.models import Document, RAGConfig, ResultSource, SearchResult
from src.core.rag.retriever import HybridRetriever

# --- Stubs with controllable behavior ---


class StubEmbedder(Embedder):
    """Returns deterministic embeddings based on text length."""

    @property
    def name(self) -> str:
        return "stub_embedder"

    @property
    def dimension(self) -> int:
        return 3

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t)), 0.1, 0.2] for t in texts]


class StubVectorStore(VectorStore):
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
        for i, doc in enumerate(list(self._docs.values())[:top_k]):
            results.append(
                SearchResult(
                    document=doc,
                    score=1.0 - i * 0.1,
                    source=ResultSource.DENSE,
                )
            )
        return results

    async def delete(self, ids: list[str]) -> None:
        for doc_id in ids:
            self._docs.pop(doc_id, None)


class StubSparseRetriever(SparseRetriever):
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
                    SearchResult(
                        document=doc,
                        score=0.8,
                        source=ResultSource.SPARSE,
                    )
                )
        return results

    async def delete(self, ids: list[str]) -> None:
        for doc_id in ids:
            self._docs.pop(doc_id, None)


class StubReranker(Reranker):
    """Reranker that boosts scores by 0.05 and tags as RERANKED."""

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
                score=r.score + 0.05,
                source=ResultSource.RERANKED,
            )
            for r in results[:top_k]
        ]
        return sorted(reranked, key=lambda r: r.score, reverse=True)


# --- Fixtures ---


@pytest.fixture
def embedder() -> StubEmbedder:
    return StubEmbedder()


@pytest.fixture
def vector_store() -> StubVectorStore:
    return StubVectorStore()


@pytest.fixture
def sparse_retriever() -> StubSparseRetriever:
    return StubSparseRetriever()


@pytest.fixture
def reranker() -> StubReranker:
    return StubReranker()


@pytest.fixture
def sample_docs() -> list[Document]:
    return [
        Document(id="d1", content="Python is great"),
        Document(id="d2", content="FastAPI is fast"),
        Document(id="d3", content="Pydantic validates data"),
    ]


# --- Tests ---


class TestHybridRetrieverDenseOnly:
    """Dense-only mode (no sparse, no reranker)."""

    async def test_retrieve_returns_results(
        self, embedder, vector_store, sample_docs
    ):
        retriever = HybridRetriever(embedder=embedder, vector_store=vector_store)
        await retriever.ingest(sample_docs)
        results = await retriever.retrieve("python", top_k=2)
        assert len(results) <= 2
        assert all(isinstance(r, SearchResult) for r in results)

    async def test_retrieve_results_have_scores(
        self, embedder, vector_store, sample_docs
    ):
        retriever = HybridRetriever(embedder=embedder, vector_store=vector_store)
        await retriever.ingest(sample_docs)
        results = await retriever.retrieve("python")
        assert all(r.score > 0 for r in results)

    async def test_ingest_computes_embeddings(self, embedder, vector_store):
        docs = [Document(id="d1", content="hello")]
        retriever = HybridRetriever(embedder=embedder, vector_store=vector_store)
        await retriever.ingest(docs)
        # Verify the document was stored with an embedding
        stored = vector_store._docs["d1"]
        assert stored.embedding is not None
        assert len(stored.embedding) == 3

    async def test_retrieve_empty_store(self, embedder, vector_store):
        retriever = HybridRetriever(embedder=embedder, vector_store=vector_store)
        results = await retriever.retrieve("anything")
        assert results == []

    async def test_delete_removes_from_store(
        self, embedder, vector_store, sample_docs
    ):
        retriever = HybridRetriever(embedder=embedder, vector_store=vector_store)
        await retriever.ingest(sample_docs)
        await retriever.delete(["d1", "d2"])
        results = await retriever.retrieve("python")
        doc_ids = {r.document.id for r in results}
        assert "d1" not in doc_ids
        assert "d2" not in doc_ids


class TestHybridRetrieverWithSparse:
    """Dense + sparse hybrid mode."""

    async def test_hybrid_returns_merged_results(
        self, embedder, vector_store, sparse_retriever, sample_docs
    ):
        retriever = HybridRetriever(
            embedder=embedder,
            vector_store=vector_store,
            sparse_retriever=sparse_retriever,
        )
        await retriever.ingest(sample_docs)
        results = await retriever.retrieve("Python")
        assert len(results) > 0

    async def test_ingest_indexes_in_both_stores(
        self, embedder, vector_store, sparse_retriever, sample_docs
    ):
        retriever = HybridRetriever(
            embedder=embedder,
            vector_store=vector_store,
            sparse_retriever=sparse_retriever,
        )
        await retriever.ingest(sample_docs)
        assert len(vector_store._docs) == 3
        assert len(sparse_retriever._docs) == 3

    async def test_delete_removes_from_both_stores(
        self, embedder, vector_store, sparse_retriever, sample_docs
    ):
        retriever = HybridRetriever(
            embedder=embedder,
            vector_store=vector_store,
            sparse_retriever=sparse_retriever,
        )
        await retriever.ingest(sample_docs)
        await retriever.delete(["d1"])
        assert "d1" not in vector_store._docs
        assert "d1" not in sparse_retriever._docs


class TestHybridRetrieverWithReranker:
    """Full pipeline: dense + sparse + reranker."""

    async def test_full_pipeline(
        self, embedder, vector_store, sparse_retriever, reranker, sample_docs
    ):
        retriever = HybridRetriever(
            embedder=embedder,
            vector_store=vector_store,
            sparse_retriever=sparse_retriever,
            reranker=reranker,
        )
        await retriever.ingest(sample_docs)
        results = await retriever.retrieve("Python")
        assert len(results) > 0
        # Reranker tags results as RERANKED
        assert all(r.source == ResultSource.RERANKED for r in results)

    async def test_reranker_disabled_via_config(
        self, embedder, vector_store, reranker, sample_docs
    ):
        config = RAGConfig(enable_reranker=False)
        retriever = HybridRetriever(
            embedder=embedder,
            vector_store=vector_store,
            reranker=reranker,
            config=config,
        )
        await retriever.ingest(sample_docs)
        results = await retriever.retrieve("Python")
        # Should NOT be reranked
        assert all(r.source != ResultSource.RERANKED for r in results)

    async def test_results_sorted_by_score_descending(
        self, embedder, vector_store, sparse_retriever, reranker, sample_docs
    ):
        retriever = HybridRetriever(
            embedder=embedder,
            vector_store=vector_store,
            sparse_retriever=sparse_retriever,
            reranker=reranker,
        )
        await retriever.ingest(sample_docs)
        results = await retriever.retrieve("Python")
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestHybridRetrieverConfig:
    """Config and top_k behavior."""

    async def test_custom_config(self, embedder, vector_store, sample_docs):
        config = RAGConfig(dense_top_k=1)
        retriever = HybridRetriever(
            embedder=embedder, vector_store=vector_store, config=config
        )
        await retriever.ingest(sample_docs)
        results = await retriever.retrieve("Python")
        assert len(results) <= 1

    async def test_top_k_override(self, embedder, vector_store, sample_docs):
        retriever = HybridRetriever(embedder=embedder, vector_store=vector_store)
        await retriever.ingest(sample_docs)
        results = await retriever.retrieve("Python", top_k=1)
        assert len(results) <= 1

    async def test_filters_passed_to_dense(self, embedder, vector_store, sample_docs):
        retriever = HybridRetriever(embedder=embedder, vector_store=vector_store)
        await retriever.ingest(sample_docs)
        # Our stub ignores filters, but verify no error
        results = await retriever.retrieve(
            "Python", filters={"source": "web"}
        )
        assert isinstance(results, list)
