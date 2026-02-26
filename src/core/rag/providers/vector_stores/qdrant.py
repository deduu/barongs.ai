"""Qdrant vector store (local Docker, in-memory, or cloud)."""

from __future__ import annotations

from typing import Any

from src.core.rag.interfaces.vector_store import VectorStore
from src.core.rag.models import Document, ResultSource, SearchResult

try:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client import models as qmodels
except ImportError:
    AsyncQdrantClient = None  # type: ignore[assignment,misc]
    qmodels = None  # type: ignore[assignment]

_INSTALL_MSG = (
    "Qdrant vector store requires: qdrant-client. "
    "Install with: pip install barongsai[rag]"
)


class QdrantVectorStore(VectorStore):
    """Qdrant vector store using ``AsyncQdrantClient``.

    Supports in-memory (``url=None``), local Docker, or Qdrant Cloud.
    """

    def __init__(
        self,
        collection_name: str = "barongsai",
        *,
        url: str | None = None,
        api_key: str | None = None,
        dimension: int = 1536,
    ) -> None:
        if AsyncQdrantClient is None:
            raise ImportError(_INSTALL_MSG)

        if url:
            self._client: AsyncQdrantClient = AsyncQdrantClient(url=url, api_key=api_key)  # type: ignore[no-untyped-call]
        else:
            self._client = AsyncQdrantClient(location=":memory:")  # type: ignore[no-untyped-call]
        self._collection = collection_name
        self._dimension = dimension
        self._collection_ensured = False

    @property
    def name(self) -> str:
        return "qdrant"

    async def _ensure_collection(self) -> None:
        if self._collection_ensured:
            return
        exists = await self._client.collection_exists(self._collection)
        if not exists:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qmodels.VectorParams(  # type: ignore[union-attr]
                    size=self._dimension,
                    distance=qmodels.Distance.COSINE,  # type: ignore[union-attr]
                ),
            )
        self._collection_ensured = True

    async def upsert(self, documents: list[Document]) -> None:
        await self._ensure_collection()
        points = [
            qmodels.PointStruct(  # type: ignore[union-attr]
                id=doc.id,
                vector=doc.embedding or [],
                payload={
                    "content": doc.content,
                    "metadata": doc.metadata,
                },
            )
            for doc in documents
        ]
        await self._client.upsert(
            collection_name=self._collection,
            points=points,
        )

    async def search(
        self,
        vector: list[float],
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        await self._ensure_collection()
        response = await self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=top_k,
        )
        results: list[SearchResult] = []
        for point in response.points:
            payload = point.payload or {}
            doc = Document(
                id=str(point.id),
                content=payload.get("content", ""),
                metadata=payload.get("metadata", {}),
            )
            results.append(
                SearchResult(document=doc, score=point.score, source=ResultSource.DENSE)
            )
        return results

    async def delete(self, ids: list[str]) -> None:
        await self._ensure_collection()
        await self._client.delete(
            collection_name=self._collection,
            points_selector=qmodels.PointIdsList(points=ids),  # type: ignore[union-attr]
        )

    async def list_documents(self, *, limit: int = 100, offset: int = 0) -> list[Document]:
        await self._ensure_collection()
        points, _next = await self._client.scroll(
            collection_name=self._collection,
            limit=limit,
            offset=offset,
        )
        docs: list[Document] = []
        for point in points:
            payload = point.payload or {}
            docs.append(
                Document(
                    id=str(point.id),
                    content=payload.get("content", ""),
                    metadata=payload.get("metadata", {}),
                )
            )
        return docs
