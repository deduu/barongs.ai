"""Cohere Rerank API provider."""

from __future__ import annotations

from src.core.rag.interfaces.reranker import Reranker
from src.core.rag.models import ResultSource, SearchResult

try:
    from cohere import AsyncClientV2 as _CohereAsyncClient

    cohere_client_cls = _CohereAsyncClient
except ImportError:
    cohere_client_cls = None  # type: ignore[assignment,misc]

_INSTALL_MSG = (
    "Cohere reranker requires: cohere. "
    "Install with: pip install barongsai[rag]"
)


class CohereReranker(Reranker):
    """Cloud reranker using the Cohere Rerank API."""

    def __init__(
        self,
        api_key: str,
        model: str = "rerank-v3.5",
    ) -> None:
        if cohere_client_cls is None:
            raise ImportError(_INSTALL_MSG)
        self._client = cohere_client_cls(api_key=api_key)  # type: ignore[misc]
        self._model = model

    @property
    def name(self) -> str:
        return "cohere"

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        *,
        top_k: int = 5,
    ) -> list[SearchResult]:
        if not results:
            return []

        documents = [r.document.content for r in results]
        response = await self._client.rerank(
            model=self._model,
            query=query,
            documents=documents,
            top_n=top_k,
        )

        reranked: list[SearchResult] = []
        for item in response.results:
            original = results[item.index]
            reranked.append(
                SearchResult(
                    document=original.document,
                    score=item.relevance_score,
                    source=ResultSource.RERANKED,
                )
            )
        return sorted(reranked, key=lambda r: r.score, reverse=True)
