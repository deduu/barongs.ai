"""Abstract base class for embedding models."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Embedder(ABC):
    """Convert text into vector embeddings.

    Implementations may use cloud APIs (OpenAI, Cohere, Voyage) or
    open-source models (sentence-transformers, fastembed).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this embedder."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the output vectors."""
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into vectors.

        Args:
            texts: Texts to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        ...
