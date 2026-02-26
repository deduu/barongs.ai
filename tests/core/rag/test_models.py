"""Tests for RAG Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.rag.models import Document, RAGConfig, ResultSource, SearchResult


class TestDocument:
    def test_create_minimal(self):
        doc = Document(id="doc-1", content="hello world")
        assert doc.id == "doc-1"
        assert doc.content == "hello world"
        assert doc.metadata == {}
        assert doc.embedding is None

    def test_create_with_embedding(self):
        vec = [0.1, 0.2, 0.3]
        doc = Document(id="doc-1", content="hello", embedding=vec)
        assert doc.embedding == vec

    def test_create_with_metadata(self):
        doc = Document(id="doc-1", content="hello", metadata={"source": "web"})
        assert doc.metadata["source"] == "web"

    def test_id_required(self):
        with pytest.raises(ValidationError):
            Document(content="hello")  # type: ignore[call-arg]

    def test_content_required(self):
        with pytest.raises(ValidationError):
            Document(id="doc-1")  # type: ignore[call-arg]


class TestResultSource:
    def test_dense_value(self):
        assert ResultSource.DENSE == "dense"

    def test_sparse_value(self):
        assert ResultSource.SPARSE == "sparse"

    def test_reranked_value(self):
        assert ResultSource.RERANKED == "reranked"


class TestSearchResult:
    def test_create(self):
        doc = Document(id="doc-1", content="hello")
        result = SearchResult(document=doc, score=0.95, source=ResultSource.DENSE)
        assert result.score == 0.95
        assert result.source == ResultSource.DENSE

    def test_score_is_float(self):
        doc = Document(id="doc-1", content="hello")
        result = SearchResult(document=doc, score=1, source=ResultSource.SPARSE)
        assert isinstance(result.score, (int, float))

    def test_document_required(self):
        with pytest.raises(ValidationError):
            SearchResult(score=0.5, source=ResultSource.DENSE)  # type: ignore[call-arg]


class TestRAGConfig:
    def test_defaults(self):
        config = RAGConfig()
        assert config.dense_weight == 0.7
        assert config.sparse_weight == 0.3
        assert config.dense_top_k == 20
        assert config.sparse_top_k == 20
        assert config.rerank_top_k == 5
        assert config.enable_reranker is True

    def test_custom_weights(self):
        config = RAGConfig(dense_weight=0.5, sparse_weight=0.5)
        assert config.dense_weight == 0.5
        assert config.sparse_weight == 0.5

    def test_weight_must_be_between_0_and_1(self):
        with pytest.raises(ValidationError):
            RAGConfig(dense_weight=1.5)

        with pytest.raises(ValidationError):
            RAGConfig(sparse_weight=-0.1)

    def test_top_k_must_be_positive(self):
        with pytest.raises(ValidationError):
            RAGConfig(dense_top_k=0)

        with pytest.raises(ValidationError):
            RAGConfig(rerank_top_k=-1)

    def test_disable_reranker(self):
        config = RAGConfig(enable_reranker=False)
        assert config.enable_reranker is False
