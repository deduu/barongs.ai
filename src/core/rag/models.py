"""Pydantic models for the RAG retrieval pipeline."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ResultSource(StrEnum):
    """Provenance of a search result."""

    DENSE = "dense"
    SPARSE = "sparse"
    RERANKED = "reranked"


class Document(BaseModel):
    """A document to be indexed and retrieved."""

    id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None


class SearchResult(BaseModel):
    """A single retrieval result with provenance."""

    document: Document
    score: float
    source: ResultSource


class RAGConfig(BaseModel):
    """Configuration for the hybrid retrieval pipeline."""

    dense_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    sparse_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    dense_top_k: int = Field(default=20, gt=0)
    sparse_top_k: int = Field(default=20, gt=0)
    rerank_top_k: int = Field(default=5, gt=0)
    enable_reranker: bool = True
