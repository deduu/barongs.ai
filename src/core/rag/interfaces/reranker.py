"""Abstract base class for reranker models."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.rag.models import SearchResult


class Reranker(ABC):
    """Re-score and reorder search results for improved relevance.

    Implementations may use cloud APIs (Cohere Rerank, Jina) or
    open-source cross-encoder models.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this reranker."""
        ...

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        *,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Rerank search results against a query.

        Args:
            query: The original search query.
            results: Candidate results to reorder.
            top_k: Maximum number of results to return.

        Returns:
            Reranked results with ``source=ResultSource.RERANKED``.
        """
        ...
