from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.applications.search_agent.agents.rag_synthesizer import RAGSynthesizerAgent
from src.applications.search_agent.models.streaming import StreamEventType
from src.core.middleware.auth import create_api_key_dependency
from src.core.models.config import AppSettings
from src.core.models.context import AgentContext
from src.core.rag.chunker import chunk_text
from src.core.rag.persistent_retriever import PersistentHybridRetriever
from src.core.rag.retriever import HybridRetriever

# --- Request / Response models ---


class IngestTextRequest(BaseModel):
    content: str
    title: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    status: str = "ok"
    chunks_ingested: int = 0
    doc_id_prefix: str = ""


class RAGSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class RAGSearchResultItem(BaseModel):
    id: str
    content: str
    score: float
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGSearchResponse(BaseModel):
    results: list[RAGSearchResultItem]


class RAGDocumentItem(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGDocumentsResponse(BaseModel):
    documents: list[RAGDocumentItem]


class RAGChatRequest(BaseModel):
    query: str
    top_k: int = 5


# --- Router factory ---


def create_rag_router(
    settings: AppSettings,
    *,
    retriever: HybridRetriever | PersistentHybridRetriever,
    synthesizer: RAGSynthesizerAgent,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    max_file_size_mb: int = 10,
) -> APIRouter:
    """Create the RAG API router with auth dependency."""
    router = APIRouter(prefix="/api/rag", tags=["rag"])
    verify_key = create_api_key_dependency(settings)

    @router.post("/ingest", response_model=IngestResponse)
    async def ingest_text(
        request: IngestTextRequest,
        _api_key: str = Depends(verify_key),
    ) -> IngestResponse:
        content = request.content.strip()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content is empty.",
            )

        doc_id_prefix = f"doc-{uuid.uuid4().hex[:8]}"
        meta = {**request.metadata}
        if request.title:
            meta["title"] = request.title

        chunks = chunk_text(
            content,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            doc_id_prefix=doc_id_prefix,
            metadata=meta,
        )

        await retriever.ingest(chunks)

        return IngestResponse(
            status="ok",
            chunks_ingested=len(chunks),
            doc_id_prefix=doc_id_prefix,
        )

    @router.post("/ingest/file", response_model=IngestResponse)
    async def ingest_file(
        file: UploadFile,
        _api_key: str = Depends(verify_key),
        title: str = "",
    ) -> IngestResponse:
        raw = await file.read()

        max_bytes = max_file_size_mb * 1024 * 1024
        if len(raw) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds {max_file_size_mb}MB limit.",
            )

        content = raw.decode("utf-8", errors="replace").strip()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content is empty.",
            )

        doc_id_prefix = f"file-{uuid.uuid4().hex[:8]}"
        meta: dict[str, Any] = {}
        if title:
            meta["title"] = title
        elif file.filename:
            meta["title"] = file.filename

        chunks = chunk_text(
            content,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            doc_id_prefix=doc_id_prefix,
            metadata=meta,
        )

        await retriever.ingest(chunks)

        return IngestResponse(
            status="ok",
            chunks_ingested=len(chunks),
            doc_id_prefix=doc_id_prefix,
        )

    @router.post("/search", response_model=RAGSearchResponse)
    async def search_documents(
        request: RAGSearchRequest,
        _api_key: str = Depends(verify_key),
    ) -> RAGSearchResponse:
        query = request.query.strip()
        if not query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query is empty.",
            )

        results = await retriever.retrieve(query, top_k=request.top_k)

        return RAGSearchResponse(
            results=[
                RAGSearchResultItem(
                    id=r.document.id,
                    content=r.document.content,
                    score=r.score,
                    source=r.source.value,
                    metadata=r.document.metadata,
                )
                for r in results
            ]
        )

    @router.get("/documents", response_model=RAGDocumentsResponse)
    async def list_documents(
        _api_key: str = Depends(verify_key),
        limit: int = 100,
        offset: int = 0,
    ) -> RAGDocumentsResponse:
        docs = await retriever._vector_store.list_documents(limit=limit, offset=offset)
        return RAGDocumentsResponse(
            documents=[
                RAGDocumentItem(
                    id=d.id,
                    content=d.content,
                    metadata=d.metadata,
                )
                for d in docs
            ]
        )

    @router.delete("/documents/{doc_id}")
    async def delete_document(
        doc_id: str,
        _api_key: str = Depends(verify_key),
    ) -> dict[str, str]:
        await retriever.delete([doc_id])
        return {"status": "ok"}

    @router.post("/chat/stream")
    async def rag_chat_stream(
        request: RAGChatRequest,
        _api_key: str = Depends(verify_key),
    ) -> EventSourceResponse:
        async def event_generator() -> AsyncGenerator[dict[str, str], None]:
            yield {
                "event": StreamEventType.STATUS,
                "data": json.dumps({"message": "Searching knowledge base..."}),
            }

            # 1. Retrieve relevant documents
            results = await retriever.retrieve(
                request.query, top_k=request.top_k
            )

            # 2. Emit sources
            rag_sources: list[dict[str, Any]] = []
            for r in results:
                source_data = {
                    "id": r.document.id,
                    "content": r.document.content,
                    "score": r.score,
                    "source": r.source.value,
                    "metadata": r.document.metadata,
                }
                rag_sources.append(source_data)
                yield {
                    "event": StreamEventType.SOURCE,
                    "data": json.dumps(source_data),
                }

            yield {
                "event": StreamEventType.STATUS,
                "data": json.dumps({"message": "Synthesizing answer..."}),
            }

            # 3. Stream synthesizer response
            synth_context = AgentContext(
                user_message=request.query,
                metadata={"rag_sources": rag_sources},
            )
            full_response = ""
            async for token in synthesizer.stream_run(synth_context):
                full_response += token
                yield {
                    "event": StreamEventType.CHUNK,
                    "data": json.dumps({"text": token}),
                }

            yield {
                "event": StreamEventType.DONE,
                "data": json.dumps(
                    {"response": full_response, "rag_sources": rag_sources}
                ),
            }

        return EventSourceResponse(event_generator())

    return router
