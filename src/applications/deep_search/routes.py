from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from src.applications.deep_search.models.api import DeepSearchRequest, DeepSearchResponse
from src.applications.deep_search.models.outline import OutlineConfirmation
from src.applications.deep_search.models.streaming import DeepSearchEventType
from src.applications.deep_search.session_store import SessionStore
from src.applications.deep_search.streaming_pipeline import StreamableDeepSearchPipeline
from src.core.interfaces.orchestrator import Orchestrator
from src.core.middleware.auth import create_api_key_dependency
from src.core.models.auth import AuthContext
from src.core.models.config import AppSettings
from src.core.models.context import AgentContext

logger = logging.getLogger(__name__)


def create_router(
    orchestrator: Orchestrator,
    settings: AppSettings,
    *,
    pipeline: StreamableDeepSearchPipeline | None = None,
    session_store: SessionStore | None = None,
    auth_dependency: Callable[..., Coroutine[Any, Any, AuthContext]] | None = None,
) -> APIRouter:
    """Create the deep search API router."""
    router = APIRouter(prefix="/api", tags=["deep-search"])
    verify_key = auth_dependency or create_api_key_dependency(settings)

    @router.post("/deep-search", response_model=DeepSearchResponse)
    async def deep_search(
        request: DeepSearchRequest,
        auth: AuthContext = Depends(verify_key),
    ) -> DeepSearchResponse:
        context = AgentContext(
            user_message=request.query,
            tenant_id=auth.tenant_id,
            session_id=request.session_id,
            metadata={
                "max_iterations": request.max_iterations,
                "max_time_seconds": request.max_time_seconds,
                "enable_code_execution": request.enable_code_execution,
                "enable_academic_search": request.enable_academic_search,
                "research_mode": request.research_mode,
            },
        )
        result = await orchestrator.run(context)

        findings = result.metadata.get("findings", [])
        sources = list({
            f.get("source_url", "")
            for f in findings if f.get("source_url")
        })

        return DeepSearchResponse(
            executive_summary=result.response[:500],
            sections=[],
            findings=findings,
            methodology_notes="",
            overall_confidence=0.5,
            sources=sources,
            research_mode=request.research_mode,
        )

    @router.post("/deep-search/stream")
    async def deep_search_stream(
        request: DeepSearchRequest,
        auth: AuthContext = Depends(verify_key),
    ) -> EventSourceResponse:
        async def event_generator() -> AsyncGenerator[dict[str, str], None]:
            try:
                if pipeline:
                    # Build settings overrides from request
                    settings_meta: dict[str, Any] = {}
                    if request.temperature is not None:
                        settings_meta["temperature"] = request.temperature
                    if request.max_sources is not None:
                        settings_meta["max_sources"] = request.max_sources
                    if request.extraction_detail is not None:
                        settings_meta["extraction_detail"] = request.extraction_detail
                    if request.crawl_depth is not None:
                        settings_meta["crawl_depth"] = request.crawl_depth

                    context = AgentContext(
                        user_message=request.query,
                        tenant_id=auth.tenant_id,
                        session_id=request.session_id,
                        metadata={
                            "max_iterations": request.max_iterations,
                            "max_time_seconds": request.max_time_seconds,
                            "enable_code_execution": request.enable_code_execution,
                            "enable_academic_search": request.enable_academic_search,
                            "research_mode": request.research_mode,
                            "interactive_outline": request.interactive_outline,
                            **settings_meta,
                        },
                    )
                    async for event in pipeline.stream_run(context):
                        yield {
                            "event": str(event["event"]),
                            "data": json.dumps(event["data"], default=str),
                        }
                else:
                    yield {
                        "event": str(DeepSearchEventType.ERROR),
                        "data": json.dumps({"error": "Streaming not configured"}),
                    }
            except Exception:
                logger.exception("Deep search SSE stream error")
                yield {
                    "event": str(DeepSearchEventType.ERROR),
                    "data": json.dumps(
                        {"error": "An internal error occurred. Please try again."}
                    ),
                }

        return EventSourceResponse(event_generator())

    @router.post("/deep-search/outline/confirm")
    async def confirm_outline(
        confirmation: OutlineConfirmation,
        auth: AuthContext = Depends(verify_key),
    ) -> dict[str, str]:
        if not session_store:
            return {"status": "error", "message": "Session store not configured"}

        session = session_store.get(confirmation.session_id)
        if not session:
            return {"status": "error", "message": "Session not found or expired"}

        response_data: dict[str, Any] = {"approved": confirmation.approved}
        if confirmation.sections is not None:
            response_data["sections"] = [s.model_dump() for s in confirmation.sections]
        if confirmation.research_tasks is not None:
            response_data["research_tasks"] = [
                t.model_dump() for t in confirmation.research_tasks
            ]

        session.confirm(response_data)
        return {"status": "ok"}

    return router
