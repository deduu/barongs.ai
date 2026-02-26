"""Abstract base class for dense vector stores."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.core.rag.models import Document, SearchResult


class VectorStore(ABC):
    """Dense vector storage and similarity search.

    Implementations may use cloud services (Pinecone, Qdrant Cloud, Weaviate)
    or local engines (FAISS, Chroma, Qdrant local, Milvus).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this vector store."""
        ...

    @abstractmethod
    async def upsert(self, documents: list[Document]) -> None:
        """Insert or update documents with their embeddings.

        Documents must have their ``embedding`` field populated.

        Args:
            documents: Documents to upsert.
        """
        ...

    @abstractmethod
    async def search(
        self,
        vector: list[float],
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Find the most similar documents to a query vector.

        Args:
            vector: Query embedding.
            top_k: Maximum number of results.
            filters: Optional metadata filters.

        Returns:
            Search results sorted by descending similarity.
        """
        ...

    @abstractmethod
    async def delete(self, ids: list[str]) -> None:
        """Delete documents by their IDs.

        Args:
            ids: Document IDs to remove.
        """
        ...

    async def list_documents(self, *, limit: int = 100, offset: int = 0) -> list[Document]:
        """List stored documents.

        Not all backends support listing. The default raises
        ``NotImplementedError``; concrete stores should override.

        Args:
            limit: Maximum documents to return.
            offset: Number of documents to skip.
        """
        raise NotImplementedError(f"{self.name} does not support list_documents")
