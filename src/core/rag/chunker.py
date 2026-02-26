"""Text chunking utility for document ingestion."""

from __future__ import annotations

from typing import Any

from src.core.rag.models import Document


def chunk_text(
    text: str,
    *,
    chunk_size: int = 1000,
    overlap: int = 200,
    doc_id_prefix: str = "chunk",
    metadata: dict[str, Any] | None = None,
) -> list[Document]:
    """Split text into overlapping chunks, each returned as a Document.

    Args:
        text: Source text to chunk.
        chunk_size: Maximum characters per chunk.
        overlap: Number of overlapping characters between consecutive chunks.
        doc_id_prefix: Prefix for generated document IDs.
        metadata: Base metadata copied to every chunk.

    Returns:
        List of Document objects with sequential IDs.
    """
    text = text.strip()
    if not text:
        return []

    base_meta = metadata or {}
    effective_overlap = min(overlap, chunk_size - 1)
    step = chunk_size - effective_overlap

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += step

    total = len(chunks)
    return [
        Document(
            id=f"{doc_id_prefix}-{i}",
            content=chunk,
            metadata={**base_meta, "chunk_index": i, "total_chunks": total},
        )
        for i, chunk in enumerate(chunks)
    ]
