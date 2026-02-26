"""Cross-encoder reranker using sentence-transformers."""

from __future__ import annotations

import asyncio

from src.core.rag.interfaces.reranker import Reranker
from src.core.rag.models import ResultSource, SearchResult

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None  # type: ignore[assignment,misc]

_INSTALL_MSG = (
    "Cross-encoder reranker requires: sentence-transformers. "
    "Install with: pip install barongsai[rag]"
)


class CrossEncoderReranker(Reranker):
    """Local reranker using a sentence-transformers CrossEncoder model.

    Inference is offloaded to a thread pool via ``asyncio.to_thread``.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> None:
        if CrossEncoder is None:
            raise ImportError(_INSTALL_MSG)
        self._model: CrossEncoder = CrossEncoder(model_name)  # type: ignore[no-untyped-call]

    @property
    def name(self) -> str:
        return "cross_encoder"

    def _sync_rerank(
        self, query: str, results: list[SearchResult], top_k: int
    ) -> list[SearchResult]:
        pairs = [[query, r.document.content] for r in results]
        scores = self._model.predict(pairs)  # type: ignore[no-untyped-call]

        scored = sorted(
            zip(results, scores, strict=True),
            key=lambda x: float(x[1]),
            reverse=True,
        )
        return [
            SearchResult(
                document=r.document,
                score=float(s),
                source=ResultSource.RERANKED,
            )
            for r, s in scored[:top_k]
        ]

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        *,
        top_k: int = 5,
    ) -> list[SearchResult]:
        if not results:
            return []
        return await asyncio.to_thread(self._sync_rerank, query, results, top_k)
