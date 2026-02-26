"""Composite hybrid retriever: dense + sparse + reranker."""

from __future__ import annotations

from typing import Any

from src.core.rag.interfaces.embedder import Embedder
from src.core.rag.interfaces.reranker import Reranker
from src.core.rag.interfaces.sparse_retriever import SparseRetriever
from src.core.rag.interfaces.vector_store import VectorStore
from src.core.rag.models import Document, RAGConfig, SearchResult


def _reciprocal_rank_fusion(
    result_lists: list[list[SearchResult]],
    weights: list[float],
    k: int = 60,
) -> list[SearchResult]:
    """Merge multiple ranked result lists using weighted Reciprocal Rank Fusion.

    RRF score for document d = sum(weight_i / (k + rank_i(d))) across all lists
    where rank is 1-based and k is a smoothing constant (default 60).
    """
    scores: dict[str, float] = {}
    doc_map: dict[str, SearchResult] = {}

    for result_list, weight in zip(result_lists, weights, strict=True):
        for rank, result in enumerate(result_list, start=1):
            doc_id = result.document.id
            scores[doc_id] = scores.get(doc_id, 0.0) + weight / (k + rank)
            # Keep the result with metadata intact
            if doc_id not in doc_map:
                doc_map[doc_id] = result

    fused = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [
        SearchResult(
            document=doc_map[doc_id].document,
            score=score,
            source=doc_map[doc_id].source,
        )
        for doc_id, score in fused
    ]


class HybridRetriever:
    """Composite retriever: embed query -> dense + sparse -> RRF merge -> rerank.

    Only ``embedder`` and ``vector_store`` are required.  When
    ``sparse_retriever`` or ``reranker`` are omitted the corresponding
    pipeline stage is skipped.
    """

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        *,
        sparse_retriever: SparseRetriever | None = None,
        reranker: Reranker | None = None,
        config: RAGConfig | None = None,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._sparse_retriever = sparse_retriever
        self._reranker = reranker
        self._config = config or RAGConfig()

    async def ingest(self, documents: list[Document]) -> None:
        """Embed documents and upsert into all configured stores."""
        texts = [doc.content for doc in documents]
        vectors = await self._embedder.embed(texts)

        docs_with_embeddings = [
            doc.model_copy(update={"embedding": vec})
            for doc, vec in zip(documents, vectors, strict=True)
        ]

        await self._vector_store.upsert(docs_with_embeddings)

        if self._sparse_retriever is not None:
            await self._sparse_retriever.index(documents)

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Run the full hybrid retrieval pipeline.

        1. Embed the query.
        2. Dense search via vector store.
        3. Sparse search (if configured).
        4. Merge via Reciprocal Rank Fusion.
        5. Rerank (if configured and enabled).
        6. Return top_k results.
        """
        cfg = self._config

        # 1. Embed query
        query_vectors = await self._embedder.embed([query])
        query_vector = query_vectors[0]

        # 2. Dense search
        dense_results = await self._vector_store.search(
            query_vector, top_k=cfg.dense_top_k, filters=filters
        )

        # 3. Sparse search (optional)
        if self._sparse_retriever is not None:
            sparse_results = await self._sparse_retriever.search(
                query, top_k=cfg.sparse_top_k, filters=filters
            )
            # 4. Merge via RRF
            merged = _reciprocal_rank_fusion(
                [dense_results, sparse_results],
                [cfg.dense_weight, cfg.sparse_weight],
            )
        else:
            merged = dense_results

        # 5. Rerank (optional)
        rerank_top_k = top_k or cfg.rerank_top_k
        if (
            self._reranker is not None
            and cfg.enable_reranker
            and merged
        ):
            results = await self._reranker.rerank(
                query, merged, top_k=rerank_top_k
            )
        else:
            results = sorted(merged, key=lambda r: r.score, reverse=True)
            results = results[:rerank_top_k]

        # 6. Apply final top_k
        if top_k is not None:
            results = results[:top_k]

        return results

    async def delete(self, ids: list[str]) -> None:
        """Delete documents from all configured stores."""
        await self._vector_store.delete(ids)
        if self._sparse_retriever is not None:
            await self._sparse_retriever.delete(ids)
