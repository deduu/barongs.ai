"""FAISS in-memory vector store for local development."""

from __future__ import annotations

import asyncio
from typing import Any

from src.core.rag.interfaces.vector_store import VectorStore
from src.core.rag.models import Document, ResultSource, SearchResult

try:
    import faiss
    import numpy as np
except ImportError:
    faiss = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]

_INSTALL_MSG = (
    "FAISS vector store requires: faiss-cpu and numpy. "
    "Install with: pip install barongsai[rag]"
)


class FAISSVectorStore(VectorStore):
    """In-memory FAISS vector store.

    Uses ``IndexFlatIP`` (inner product) on L2-normalised vectors
    for cosine similarity search.  All blocking operations are
    offloaded via ``asyncio.to_thread``.
    """

    def __init__(self, dimension: int = 1536) -> None:
        if faiss is None:
            raise ImportError(_INSTALL_MSG)

        self._dimension = dimension
        self._index: faiss.IndexFlatIP = faiss.IndexFlatIP(dimension)  # type: ignore[attr-defined]
        self._docs: dict[str, Document] = {}
        self._id_to_idx: dict[str, int] = {}

    @property
    def name(self) -> str:
        return "faiss"

    def _rebuild_index(self) -> None:
        """Rebuild the FAISS index from current docs."""
        self._index = faiss.IndexFlatIP(self._dimension)  # type: ignore[attr-defined]
        self._id_to_idx.clear()
        if not self._docs:
            return
        vectors = []
        for i, (doc_id, doc) in enumerate(self._docs.items()):
            self._id_to_idx[doc_id] = i
            vec = doc.embedding or [0.0] * self._dimension
            vectors.append(vec)
        arr = np.array(vectors, dtype=np.float32)  # type: ignore[union-attr]
        # L2-normalise for cosine similarity via inner product
        norms = np.linalg.norm(arr, axis=1, keepdims=True)  # type: ignore[union-attr]
        norms = np.maximum(norms, 1e-10)  # type: ignore[union-attr]
        arr = arr / norms
        self._index.add(arr)  # type: ignore[union-attr]

    async def upsert(self, documents: list[Document]) -> None:
        for doc in documents:
            self._docs[doc.id] = doc
        await asyncio.to_thread(self._rebuild_index)

    def _sync_search(self, vector: list[float], top_k: int) -> list[SearchResult]:
        if self._index.ntotal == 0:  # type: ignore[union-attr]
            return []
        arr = np.array([vector], dtype=np.float32)  # type: ignore[union-attr]
        norms = np.linalg.norm(arr, axis=1, keepdims=True)  # type: ignore[union-attr]
        norms = np.maximum(norms, 1e-10)  # type: ignore[union-attr]
        arr = arr / norms
        k = min(top_k, self._index.ntotal)  # type: ignore[union-attr]
        scores, indices = self._index.search(arr, k)  # type: ignore[union-attr]

        idx_to_id = {v: k for k, v in self._id_to_idx.items()}
        results: list[SearchResult] = []
        for score, idx in zip(scores[0], indices[0], strict=True):
            if idx == -1:
                continue
            doc_id = idx_to_id.get(int(idx))
            if doc_id and doc_id in self._docs:
                results.append(
                    SearchResult(
                        document=self._docs[doc_id],
                        score=float(score),
                        source=ResultSource.DENSE,
                    )
                )
        return results

    async def search(
        self,
        vector: list[float],
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        return await asyncio.to_thread(self._sync_search, vector, top_k)

    async def delete(self, ids: list[str]) -> None:
        for doc_id in ids:
            self._docs.pop(doc_id, None)
        await asyncio.to_thread(self._rebuild_index)

    async def list_documents(self, *, limit: int = 100, offset: int = 0) -> list[Document]:
        all_docs = list(self._docs.values())
        return all_docs[offset : offset + limit]
