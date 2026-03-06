from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from src.applications.deep_search.models.api import DeepSearchRequest, DeepSearchResponse
from src.applications.deep_search.models.outline import (
    DisambiguationConfirmation,
    OutlineConfirmation,
)
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
    stream_max_concurrent_requests: int | None = None,
    auth_dependency: Callable[..., Coroutine[Any, Any, AuthContext]] | None = None,
) -> APIRouter:
    """Create the deep search API router."""
    router = APIRouter(prefix="/api", tags=["deep-search"])
    verify_key = auth_dependency or create_api_key_dependency(settings)
    stream_state = {"active": 0}
    stream_slots_lock = asyncio.Lock()

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
        result = await orchestrator.run(
            context,
            timeout_seconds=float(request.max_time_seconds),
        )

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
        request_id = request.session_id or f"ds-{uuid.uuid4().hex[:8]}"
        if (
            stream_max_concurrent_requests is not None
            and stream_max_concurrent_requests > 0
        ):
            async with stream_slots_lock:
                if stream_state["active"] >= stream_max_concurrent_requests:
                    raise HTTPException(
                        status_code=429,
                        detail=(
                            "Deep search is at capacity. Please retry in a moment."
                        ),
                    )
                stream_state["active"] += 1

        async def event_generator() -> AsyncGenerator[dict[str, str], None]:
            try:
                if pipeline:
                    logger.info(
                        "Deep search stream opened: request_id=%s mode=%s query=%s",
                        request_id,
                        request.research_mode,
                        request.query[:160],
                    )
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
                        if event["event"] == DeepSearchEventType.CHUNK:
                            logger.debug(
                                "Deep search stream chunk: request_id=%s size=%s",
                                request_id,
                                len(str(event["data"].get("token", ""))),
                            )
                        else:
                            logger.info(
                                "Deep search stream event: request_id=%s event=%s data=%s",
                                request_id,
                                str(event["event"]),
                                event["data"],
                            )
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
                logger.exception("Deep search SSE stream error: request_id=%s", request_id)
                yield {
                    "event": str(DeepSearchEventType.ERROR),
                    "data": json.dumps(
                        {"error": "An internal error occurred. Please try again."}
                    ),
                }
            finally:
                logger.info("Deep search stream closed: request_id=%s", request_id)
                if (
                    stream_max_concurrent_requests is not None
                    and stream_max_concurrent_requests > 0
                ):
                    async with stream_slots_lock:
                        stream_state["active"] = max(0, stream_state["active"] - 1)

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

    @router.post("/deep-search/disambiguate/confirm")
    async def confirm_disambiguation(
        confirmation: DisambiguationConfirmation,
        auth: AuthContext = Depends(verify_key),
    ) -> dict[str, str]:
        if not session_store:
            return {"status": "error", "message": "Session store not configured"}

        session = session_store.get(confirmation.session_id)
        if not session:
            return {"status": "error", "message": "Session not found or expired"}

        session.confirm({"clarification": confirmation.clarification})
        return {"status": "ok"}

    return router
