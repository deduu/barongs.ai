from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.applications.search_agent.agents.synthesizer import SynthesizerAgent
from src.applications.search_agent.models.streaming import StreamEventType
from src.core.interfaces.agent import Agent
from src.core.interfaces.orchestrator import Orchestrator
from src.core.jobs.service import JobService
from src.core.middleware.auth import create_api_key_dependency
from src.core.models.auth import AuthContext
from src.core.models.config import AppSettings
from src.core.models.context import AgentContext

logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str
    session_id: str | None = None


class SearchResponse(BaseModel):
    response: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    query_type: str = ""
    agent_name: str = ""


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    agent_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AsyncSearchResponse(BaseModel):
    job_id: str


def create_router(
    orchestrator: Orchestrator,
    settings: AppSettings,
    *,
    web_researcher: Agent | None = None,
    synthesizer: SynthesizerAgent | None = None,
    auth_dependency: Callable[..., Coroutine[Any, Any, AuthContext]] | None = None,
    job_service: JobService | None = None,
) -> APIRouter:
    """Create the search agent router with auth dependency."""
    router = APIRouter(prefix="/api", tags=["search"])
    verify_key = auth_dependency or create_api_key_dependency(settings)

    @router.post("/search", response_model=SearchResponse)
    async def search(
        request: SearchRequest,
        auth: AuthContext = Depends(verify_key),
    ) -> SearchResponse:
        context = AgentContext(
            user_message=request.query,
            tenant_id=auth.tenant_id,
            session_id=request.session_id,
        )
        result = await orchestrator.run(context)

        return SearchResponse(
            response=result.response,
            sources=result.metadata.get("sources", []),
            query_type=result.metadata.get("query_type", ""),
            agent_name=result.agent_name,
        )

    @router.post("/search/stream")
    async def search_stream(
        request: SearchRequest,
        auth: AuthContext = Depends(verify_key),
    ) -> EventSourceResponse:
        async def event_generator() -> AsyncGenerator[dict[str, str], None]:
            try:
                # If sub-agents are available, stream incrementally
                if web_researcher and synthesizer:
                    yield {
                        "event": StreamEventType.STATUS,
                        "data": json.dumps({"message": "Searching..."}),
                    }

                    # Step 1: Run web researcher
                    context = AgentContext(
                        user_message=request.query,
                        tenant_id=auth.tenant_id,
                        session_id=request.session_id,
                        metadata={"refined_queries": [request.query]},
                    )
                    research_result = await web_researcher.run(context)
                    sources: list[dict[str, Any]] = research_result.metadata.get(
                        "sources", []
                    )

                    # Emit sources as they're available
                    for source in sources:
                        yield {
                            "event": StreamEventType.SOURCE,
                            "data": json.dumps(source),
                        }

                    yield {
                        "event": StreamEventType.STATUS,
                        "data": json.dumps({"message": "Synthesizing..."}),
                    }

                    # Step 2: Stream synthesizer tokens
                    synth_context = AgentContext(
                        user_message=request.query,
                        tenant_id=auth.tenant_id,
                        session_id=request.session_id,
                        metadata={"sources": sources},
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
                            {"response": full_response, "sources": sources}
                        ),
                    }
                else:
                    # Fallback: non-streaming via orchestrator
                    yield {
                        "event": StreamEventType.STATUS,
                        "data": json.dumps({"message": "Searching..."}),
                    }

                    context = AgentContext(
                        user_message=request.query,
                        tenant_id=auth.tenant_id,
                        session_id=request.session_id,
                    )
                    result = await orchestrator.run(context)

                    for source in result.metadata.get("sources", []):
                        yield {
                            "event": StreamEventType.SOURCE,
                            "data": json.dumps(source),
                        }

                    yield {
                        "event": StreamEventType.CHUNK,
                        "data": json.dumps({"text": result.response}),
                    }

                    yield {
                        "event": StreamEventType.DONE,
                        "data": json.dumps(
                            {
                                "response": result.response,
                                "sources": result.metadata.get("sources", []),
                            }
                        ),
                    }
            except Exception:
                logger.exception("SSE stream error")
                yield {
                    "event": StreamEventType.ERROR,
                    "data": json.dumps(
                        {"error": "An internal error occurred. Please try again."}
                    ),
                }

        return EventSourceResponse(event_generator())

    @router.post("/chat", response_model=ChatResponse)
    async def chat(
        request: ChatRequest,
        auth: AuthContext = Depends(verify_key),
    ) -> ChatResponse:
        context = AgentContext(
            user_message=request.message,
            tenant_id=auth.tenant_id,
            session_id=request.session_id,
        )
        result = await orchestrator.run(context)

        return ChatResponse(
            response=result.response,
            agent_name=result.agent_name,
            metadata=result.metadata,
        )

    if job_service is not None:

        @router.post(
            "/search/async",
            response_model=AsyncSearchResponse,
            status_code=202,
        )
        async def search_async(
            request: SearchRequest,
            auth: AuthContext = Depends(verify_key),
        ) -> AsyncSearchResponse:
            """Submit a search job for background processing.

            Returns 202 Accepted with a job_id. Poll ``GET /api/jobs/{job_id}``
            for results.
            """
            job_id = await job_service.submit(
                "run_search",
                query=request.query,
                session_id=request.session_id,
                tenant_id=auth.tenant_id,
            )
            return AsyncSearchResponse(job_id=job_id)

    return router
