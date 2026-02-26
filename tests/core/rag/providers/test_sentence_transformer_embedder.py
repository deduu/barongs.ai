"""Tests for Sentence Transformer embedder."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.rag.providers.embedders.sentence_transformer import (
    SentenceTransformerEmbedder,
)


@pytest.fixture
def mock_st_model():
    model = MagicMock()
    model.get_sentence_embedding_dimension.return_value = 384
    model.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    return model


@pytest.fixture
def embedder(mock_st_model):
    with patch(
        "src.core.rag.providers.embedders.sentence_transformer.SentenceTransformer",
        return_value=mock_st_model,
    ):
        return SentenceTransformerEmbedder(model_name="all-MiniLM-L6-v2")


class TestSentenceTransformerProperties:
    def test_name(self, embedder):
        assert embedder.name == "sentence_transformer"

    def test_dimension(self, embedder):
        assert embedder.dimension == 384


class TestSentenceTransformerEmbed:
    async def test_embed_texts(self, embedder, mock_st_model):
        results = await embedder.embed(["hello", "world"])
        assert len(results) == 2
        mock_st_model.encode.assert_called_once()

    async def test_empty_list(self, embedder):
        results = await embedder.embed([])
        assert results == []

    async def test_returns_list_of_lists(self, embedder):
        results = await embedder.embed(["hello", "world"])
        assert isinstance(results, list)
        assert isinstance(results[0], list)
