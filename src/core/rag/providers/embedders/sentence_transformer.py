"""Sentence Transformers embedding provider (local / open-source)."""

from __future__ import annotations

import asyncio

from src.core.rag.interfaces.embedder import Embedder

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore[assignment,misc]

_INSTALL_MSG = (
    "SentenceTransformer embedder requires: sentence-transformers. "
    "Install with: pip install barongsai[rag]"
)


class SentenceTransformerEmbedder(Embedder):
    """Local embedder using sentence-transformers models.

    Inference is offloaded to a thread pool via ``asyncio.to_thread``
    to avoid blocking the event loop.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
    ) -> None:
        if SentenceTransformer is None:
            raise ImportError(_INSTALL_MSG)

        self._model: SentenceTransformer = SentenceTransformer(model_name, device=device)  # type: ignore[no-untyped-call]
        self._dimension: int = self._model.get_sentence_embedding_dimension()  # type: ignore[no-untyped-call]

    @property
    def name(self) -> str:
        return "sentence_transformer"

    @property
    def dimension(self) -> int:
        return self._dimension

    def _sync_embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts)  # type: ignore[no-untyped-call]
        return [list(map(float, vec)) for vec in embeddings]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._sync_embed, texts)
