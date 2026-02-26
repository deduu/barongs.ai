"""Tests for Cohere reranker."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.rag.models import Document, ResultSource, SearchResult
from src.core.rag.providers.rerankers.cohere import CohereReranker


@pytest.fixture
def mock_cohere_client():
    client = AsyncMock()
    # Mock rerank response
    result1 = MagicMock()
    result1.index = 0
    result1.relevance_score = 0.95
    result2 = MagicMock()
    result2.index = 1
    result2.relevance_score = 0.60
    response = MagicMock()
    response.results = [result1, result2]
    client.rerank = AsyncMock(return_value=response)
    return client


@pytest.fixture
def reranker(mock_cohere_client):
    with patch(
        "src.core.rag.providers.rerankers.cohere.cohere_client_cls",
        return_value=mock_cohere_client,
    ):
        return CohereReranker(api_key="test-key")


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
            source=ResultSource.SPARSE,
        ),
    ]


class TestCohereProperties:
    def test_name(self, reranker):
        assert reranker.name == "cohere"


class TestCohereRerank:
    async def test_rerank_returns_results(self, reranker, sample_results):
        results = await reranker.rerank("Python", sample_results, top_k=2)
        assert len(results) == 2
        assert all(r.source == ResultSource.RERANKED for r in results)

    async def test_scores_from_cohere(self, reranker, sample_results):
        results = await reranker.rerank("Python", sample_results, top_k=2)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    async def test_rerank_empty_results(self, reranker):
        results = await reranker.rerank("Python", [], top_k=5)
        assert results == []

    async def test_rerank_calls_api(self, reranker, sample_results, mock_cohere_client):
        await reranker.rerank("Python", sample_results, top_k=2)
        mock_cohere_client.rerank.assert_called_once()

    async def test_api_error_propagates(self, reranker, sample_results, mock_cohere_client):
        mock_cohere_client.rerank.side_effect = RuntimeError("API error")
        with pytest.raises(RuntimeError, match="API error"):
            await reranker.rerank("Python", sample_results)
