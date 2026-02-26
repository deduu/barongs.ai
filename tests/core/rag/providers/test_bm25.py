"""Tests for BM25 sparse retriever."""

from __future__ import annotations

import pytest

from src.core.rag.models import Document, ResultSource
from src.core.rag.providers.sparse_retrievers.bm25 import BM25Retriever


@pytest.fixture
def retriever():
    return BM25Retriever()


@pytest.fixture
def sample_docs():
    return [
        Document(id="d1", content="Python is a great programming language"),
        Document(id="d2", content="FastAPI is a fast web framework"),
        Document(id="d3", content="Pydantic validates data models"),
    ]


class TestBM25Properties:
    def test_name(self, retriever):
        assert retriever.name == "bm25"


class TestBM25Index:
    async def test_index_stores_docs(self, retriever, sample_docs):
        await retriever.index(sample_docs)
        results = await retriever.search("Python", top_k=10)
        assert len(results) >= 1


class TestBM25Search:
    async def test_search_finds_relevant(self, retriever, sample_docs):
        await retriever.index(sample_docs)
        results = await retriever.search("Python programming")
        assert len(results) >= 1
        assert results[0].document.id == "d1"
        assert results[0].source == ResultSource.SPARSE

    async def test_search_empty_index(self, retriever):
        results = await retriever.search("anything")
        assert results == []

    async def test_search_respects_top_k(self, retriever, sample_docs):
        await retriever.index(sample_docs)
        results = await retriever.search("a", top_k=1)
        assert len(results) <= 1

    async def test_scores_sorted_descending(self, retriever, sample_docs):
        await retriever.index(sample_docs)
        results = await retriever.search("fast framework", top_k=3)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestBM25Delete:
    async def test_delete_removes_document(self, retriever, sample_docs):
        await retriever.index(sample_docs)
        await retriever.delete(["d1"])
        results = await retriever.search("Python", top_k=10)
        doc_ids = {r.document.id for r in results}
        assert "d1" not in doc_ids

    async def test_delete_nonexistent_is_noop(self, retriever, sample_docs):
        await retriever.index(sample_docs)
        await retriever.delete(["nonexistent"])
        results = await retriever.search("Python", top_k=10)
        assert len(results) >= 1
