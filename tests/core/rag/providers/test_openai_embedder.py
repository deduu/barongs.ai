"""Tests for OpenAI/Azure embedder."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.rag.providers.embedders.openai import OpenAIEmbedder


@pytest.fixture
def mock_openai_client():
    """Mock AsyncOpenAI client."""
    client = AsyncMock()
    embedding_obj = MagicMock()
    embedding_obj.embedding = [0.1, 0.2, 0.3]
    response = MagicMock()
    response.data = [embedding_obj]
    client.embeddings.create = AsyncMock(return_value=response)
    return client


@pytest.fixture
def embedder(mock_openai_client):
    with patch(
        "src.core.rag.providers.embedders.openai.AsyncOpenAI",
        return_value=mock_openai_client,
    ):
        return OpenAIEmbedder(api_key="test-key", model="text-embedding-3-small")


class TestOpenAIEmbedderProperties:
    def test_name(self, embedder):
        assert embedder.name == "openai"

    def test_dimension(self, embedder):
        assert embedder.dimension == 1536

    def test_custom_dimension(self, mock_openai_client):
        with patch(
            "src.core.rag.providers.embedders.openai.AsyncOpenAI",
            return_value=mock_openai_client,
        ):
            e = OpenAIEmbedder(api_key="k", dimension=768)
            assert e.dimension == 768


class TestOpenAIEmbedderEmbed:
    async def test_single_text(self, embedder, mock_openai_client):
        results = await embedder.embed(["hello"])
        assert len(results) == 1
        assert results[0] == [0.1, 0.2, 0.3]
        mock_openai_client.embeddings.create.assert_called_once()

    async def test_multiple_texts(self, embedder, mock_openai_client):
        emb1 = MagicMock()
        emb1.embedding = [0.1, 0.2, 0.3]
        emb2 = MagicMock()
        emb2.embedding = [0.4, 0.5, 0.6]
        response = MagicMock()
        response.data = [emb1, emb2]
        mock_openai_client.embeddings.create = AsyncMock(return_value=response)

        results = await embedder.embed(["hello", "world"])
        assert len(results) == 2

    async def test_passes_model(self, embedder, mock_openai_client):
        await embedder.embed(["hello"])
        call_kwargs = mock_openai_client.embeddings.create.call_args
        assert call_kwargs.kwargs["model"] == "text-embedding-3-small"

    async def test_empty_list(self, embedder):
        results = await embedder.embed([])
        assert results == []

    async def test_base_url_for_azure(self, mock_openai_client):
        with patch(
            "src.core.rag.providers.embedders.openai.AsyncOpenAI",
            return_value=mock_openai_client,
        ) as mock_cls:
            OpenAIEmbedder(
                api_key="azure-key",
                base_url="https://myresource.openai.azure.com/openai/v1/",
            )
            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args.kwargs
            assert "https://myresource.openai.azure.com" in call_kwargs["base_url"]

    async def test_api_error_propagates(self, embedder, mock_openai_client):
        mock_openai_client.embeddings.create.side_effect = RuntimeError("API down")
        with pytest.raises(RuntimeError, match="API down"):
            await embedder.embed(["hello"])
