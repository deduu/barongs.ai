"""Tests for text chunking utility."""

from __future__ import annotations

from src.core.rag.chunker import chunk_text


class TestChunkText:
    def test_single_chunk(self):
        text = "Hello world"
        docs = chunk_text(text, chunk_size=100, overlap=0)
        assert len(docs) == 1
        assert docs[0].content == "Hello world"
        assert docs[0].id == "chunk-0"

    def test_multiple_chunks(self):
        text = "a" * 100
        docs = chunk_text(text, chunk_size=30, overlap=10)
        assert len(docs) >= 3
        # Each chunk should be at most chunk_size
        for doc in docs:
            assert len(doc.content) <= 30

    def test_overlap(self):
        text = "0123456789" * 5  # 50 chars
        docs = chunk_text(text, chunk_size=20, overlap=5)
        assert len(docs) >= 2
        # Overlapping portion should appear in consecutive chunks
        for i in range(len(docs) - 1):
            tail = docs[i].content[-5:]
            head = docs[i + 1].content[:5]
            assert tail == head

    def test_custom_prefix(self):
        docs = chunk_text("hello world", chunk_size=100, doc_id_prefix="mydoc")
        assert docs[0].id == "mydoc-0"

    def test_metadata_propagated(self):
        meta = {"source": "test.txt", "author": "me"}
        docs = chunk_text("hello", chunk_size=100, metadata=meta)
        assert docs[0].metadata["source"] == "test.txt"
        assert docs[0].metadata["author"] == "me"
        assert docs[0].metadata["chunk_index"] == 0

    def test_empty_text(self):
        docs = chunk_text("", chunk_size=100)
        assert docs == []

    def test_whitespace_only(self):
        docs = chunk_text("   ", chunk_size=100)
        assert docs == []

    def test_exact_chunk_size(self):
        text = "a" * 50
        docs = chunk_text(text, chunk_size=50, overlap=0)
        assert len(docs) == 1
        assert docs[0].content == text

    def test_chunk_metadata_includes_total(self):
        text = "a" * 100
        docs = chunk_text(text, chunk_size=30, overlap=0)
        for doc in docs:
            assert doc.metadata["total_chunks"] == len(docs)
