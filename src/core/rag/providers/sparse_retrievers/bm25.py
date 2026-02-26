"""BM25 sparse retriever using rank-bm25."""

from __future__ import annotations

import asyncio
from typing import Any

from src.core.rag.interfaces.sparse_retriever import SparseRetriever
from src.core.rag.models import Document, ResultSource, SearchResult

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None  # type: ignore[assignment,misc]

_INSTALL_MSG = (
    "BM25 retriever requires: rank-bm25. "
    "Install with: pip install barongsai[rag]"
)


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


class BM25Retriever(SparseRetriever):
    """In-memory BM25 sparse retriever.

    The index is rebuilt from scratch on every ``index`` or ``delete``
    call because ``BM25Okapi`` does not support incremental updates.
    """

    def __init__(self) -> None:
        if BM25Okapi is None:
            raise ImportError(_INSTALL_MSG)
        self._docs: dict[str, Document] = {}
        self._bm25: BM25Okapi | None = None  # type: ignore[no-any-unimported]
        self._ordered_ids: list[str] = []

    @property
    def name(self) -> str:
        return "bm25"

    def _rebuild(self) -> None:
        self._ordered_ids = list(self._docs.keys())
        if not self._ordered_ids:
            self._bm25 = None
            return
        corpus = [_tokenize(self._docs[did].content) for did in self._ordered_ids]
        self._bm25 = BM25Okapi(corpus)  # type: ignore[no-untyped-call]

    async def index(self, documents: list[Document]) -> None:
        for doc in documents:
            self._docs[doc.id] = doc
        await asyncio.to_thread(self._rebuild)

    def _sync_search(self, query: str, top_k: int) -> list[SearchResult]:
        if self._bm25 is None or not self._ordered_ids:
            return []
        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)  # type: ignore[union-attr]
        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results: list[SearchResult] = []
        for idx, score in indexed[:top_k]:
            if score <= 0:
                continue
            doc_id = self._ordered_ids[idx]
            results.append(
                SearchResult(
                    document=self._docs[doc_id],
                    score=float(score),
                    source=ResultSource.SPARSE,
                )
            )
        return results

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        return await asyncio.to_thread(self._sync_search, query, top_k)

    async def delete(self, ids: list[str]) -> None:
        for doc_id in ids:
            self._docs.pop(doc_id, None)
        await asyncio.to_thread(self._rebuild)
