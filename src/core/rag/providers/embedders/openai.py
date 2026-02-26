"""OpenAI / Azure OpenAI embedding provider."""

from __future__ import annotations

import httpx
from openai import AsyncOpenAI

from src.core.rag.interfaces.embedder import Embedder


class OpenAIEmbedder(Embedder):
    """Embedder using the OpenAI embeddings API.

    Supports standard OpenAI and Azure OpenAI via ``base_url``.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        *,
        base_url: str | None = None,
        dimension: int = 1536,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=httpx.Timeout(15.0, connect=5.0),
        )
        self._model = model
        self._dimension = dimension

    @property
    def name(self) -> str:
        return "openai"

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = await self._client.embeddings.create(
            input=texts,
            model=self._model,
        )
        return [item.embedding for item in response.data]
