"""Tests for Cross-encoder reranker."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.rag.models import Document, ResultSource, SearchResult
from src.core.rag.providers.rerankers.cross_encoder import CrossEncoderReranker


@pytest.fixture
def mock_ce_model():
    model = MagicMock()
    # predict returns scores for each query-doc pair
    model.predict.return_value = [0.9, 0.3, 0.7]
    return model


@pytest.fixture
def reranker(mock_ce_model):
    with patch(
        "src.core.rag.providers.rerankers.cross_encoder.CrossEncoder",
        return_value=mock_ce_model,
    ):
        return CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")


@pytest.fixture
def sample_results():
    return [
        SearchResult(
            document=Document(id="d1", content="Python guide"),
            score=0.8,
            source=ResultSource.DENSE,
        ),
        SearchResult(
            document=Document(id="d2", content="Java tutorial"),
            score=0.7,
            source=ResultSource.DENSE,
        ),
        SearchResult(
            document=Document(id="d3", content="Python tricks"),
            score=0.6,
            source=ResultSource.SPARSE,
        ),
    ]


class TestCrossEncoderProperties:
    def test_name(self, reranker):
        assert reranker.name == "cross_encoder"


class TestCrossEncoderRerank:
    async def test_rerank_reorders(self, reranker, sample_results):
        results = await reranker.rerank("Python", sample_results, top_k=3)
        assert len(results) == 3
        # Highest CE score (0.9) should be first
        assert results[0].document.id == "d1"
        assert results[0].source == ResultSource.RERANKED

    async def test_rerank_respects_top_k(self, reranker, sample_results):
        results = await reranker.rerank("Python", sample_results, top_k=1)
        assert len(results) == 1

    async def test_rerank_empty_results(self, reranker):
        results = await reranker.rerank("Python", [], top_k=5)
        assert results == []

    async def test_scores_from_cross_encoder(self, reranker, sample_results):
        results = await reranker.rerank("Python", sample_results, top_k=3)
        # Scores should be the CE model scores, sorted descending
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)
