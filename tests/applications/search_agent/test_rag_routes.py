from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.applications.search_agent.agents.rag_synthesizer import RAGSynthesizerAgent
from src.applications.search_agent.rag_routes import create_rag_router
from src.core.models.config import AppSettings
from src.core.rag.models import Document, ResultSource, SearchResult
from src.core.rag.retriever import HybridRetriever


def _make_app(
    retriever: HybridRetriever | None = None,
    synthesizer: RAGSynthesizerAgent | None = None,
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    max_file_size_mb: int = 10,
) -> Any:
    """Create a minimal FastAPI app with the RAG router for testing."""
    from fastapi import FastAPI

    app = FastAPI()
    settings = AppSettings(app_name="test", api_key="test-key")
    router = create_rag_router(
        settings,
        retriever=retriever or AsyncMock(spec=HybridRetriever),
        synthesizer=synthesizer or AsyncMock(spec=RAGSynthesizerAgent),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        max_file_size_mb=max_file_size_mb,
    )
    app.include_router(router)
    return app


def _auth_headers() -> dict[str, str]:
    return {"X-API-Key": "test-key"}


class TestRAGIngestText:
    async def test_ingest_text_success(self) -> None:
        retriever = AsyncMock(spec=HybridRetriever)
        retriever.ingest = AsyncMock()
        app = _make_app(retriever=retriever, chunk_size=100, chunk_overlap=20)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/rag/ingest",
                json={
                    "content": "Hello world. " * 50,
                    "title": "Test Document",
                },
                headers=_auth_headers(),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["chunks_ingested"] > 0
        retriever.ingest.assert_called_once()

    async def test_ingest_text_empty_content(self) -> None:
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/rag/ingest",
                json={"content": "   ", "title": "Empty"},
                headers=_auth_headers(),
            )

        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    async def test_ingest_text_no_auth(self) -> None:
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/rag/ingest",
                json={"content": "test", "title": "t"},
            )

        assert resp.status_code in (401, 403)


class TestRAGIngestFile:
    async def test_ingest_file_txt(self) -> None:
        retriever = AsyncMock(spec=HybridRetriever)
        retriever.ingest = AsyncMock()
        app = _make_app(retriever=retriever, chunk_size=50, chunk_overlap=10)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/rag/ingest/file",
                files={"file": ("test.txt", b"Hello world content " * 20, "text/plain")},
                data={"title": "My File"},
                headers=_auth_headers(),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["chunks_ingested"] > 0

    async def test_ingest_file_too_large(self) -> None:
        app = _make_app(max_file_size_mb=1)

        # Create content slightly over 1MB
        big_content = b"x" * (1 * 1024 * 1024 + 1)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/rag/ingest/file",
                files={"file": ("big.txt", big_content, "text/plain")},
                headers=_auth_headers(),
            )

        assert resp.status_code == 413


class TestRAGSearch:
    async def test_search_returns_results(self) -> None:
        retriever = AsyncMock(spec=HybridRetriever)
        retriever.retrieve = AsyncMock(
            return_value=[
                SearchResult(
                    document=Document(
                        id="doc-0",
                        content="Found content",
                        metadata={"title": "Test"},
                    ),
                    score=0.95,
                    source=ResultSource.DENSE,
                ),
            ]
        )
        app = _make_app(retriever=retriever)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/rag/search",
                json={"query": "test query", "top_k": 5},
                headers=_auth_headers(),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == "doc-0"
        assert data["results"][0]["score"] == pytest.approx(0.95)

    async def test_search_empty_query(self) -> None:
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/rag/search",
                json={"query": "  "},
                headers=_auth_headers(),
            )

        assert resp.status_code == 400


class TestRAGDocuments:
    async def test_list_documents(self) -> None:
        retriever = AsyncMock(spec=HybridRetriever)
        retriever._vector_store = AsyncMock()
        retriever._vector_store.list_documents = AsyncMock(
            return_value=[
                Document(id="d1", content="c1", metadata={"title": "Doc 1"}),
                Document(id="d2", content="c2", metadata={"title": "Doc 2"}),
            ]
        )
        app = _make_app(retriever=retriever)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/rag/documents",
                headers=_auth_headers(),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["documents"]) == 2

    async def test_delete_document(self) -> None:
        retriever = AsyncMock(spec=HybridRetriever)
        retriever.delete = AsyncMock()
        app = _make_app(retriever=retriever)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete(
                "/api/rag/documents/doc-123",
                headers=_auth_headers(),
            )

        assert resp.status_code == 200
        retriever.delete.assert_called_once_with(["doc-123"])


class TestRAGChatStream:
    async def test_stream_emits_correct_events(self) -> None:
        retriever = AsyncMock(spec=HybridRetriever)
        retriever.retrieve = AsyncMock(
            return_value=[
                SearchResult(
                    document=Document(
                        id="chunk-0",
                        content="Relevant content",
                        metadata={"title": "Src Doc"},
                    ),
                    score=0.9,
                    source=ResultSource.DENSE,
                ),
            ]
        )

        mock_llm = AsyncMock()
        tokens = ["Answer", " from", " KB."]

        async def mock_stream(_req: object) -> Any:
            for t in tokens:
                yield t

        mock_llm.stream = mock_stream
        synth = RAGSynthesizerAgent(llm_provider=mock_llm, model="gpt-4o")

        app = _make_app(retriever=retriever, synthesizer=synth)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/rag/chat/stream",
                json={"query": "What is in the KB?"},
                headers=_auth_headers(),
            )

        assert resp.status_code == 200

        # Parse SSE events from the response body (handle \r\n from sse_starlette)
        text = resp.text.replace("\r\n", "\n").strip()
        blocks = text.split("\n\n")
        events: list[dict[str, str]] = []
        for block in blocks:
            current: dict[str, str] = {}
            for line in block.strip().split("\n"):
                if line.startswith("event:"):
                    current["event"] = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    current["data"] = line[len("data:"):].strip()
            if current:
                events.append(current)

        event_types = [e["event"] for e in events if "event" in e]
        assert "status" in event_types
        assert "source" in event_types
        assert "chunk" in event_types
        assert "done" in event_types
