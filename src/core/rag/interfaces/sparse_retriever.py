"""Abstract base class for sparse retrieval engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.core.rag.models import Document, SearchResult


class SparseRetriever(ABC):
    """Keyword / sparse retrieval (BM25, TF-IDF, SPLADE, etc.).

    Operates on raw text queries rather than embedding vectors.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this sparse retriever."""
        ...

    @abstractmethod
    async def index(self, documents: list[Document]) -> None:
        """Index documents for sparse retrieval.

        Args:
            documents: Documents to index.
        """
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search using keyword / sparse matching.

        Args:
            query: Raw text query.
            top_k: Maximum number of results.
            filters: Optional metadata filters.

        Returns:
            Search results sorted by descending relevance.
        """
        ...

    @abstractmethod
    async def delete(self, ids: list[str]) -> None:
        """Delete documents by their IDs.

        Args:
            ids: Document IDs to remove.
        """
        ...
