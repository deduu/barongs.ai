from __future__ import annotations

__all__: list[str] = []

try:
    from src.core.rag.providers.sparse_retrievers.bm25 import BM25Retriever  # noqa: F401

    __all__.append("BM25Retriever")
except ImportError:
    pass
