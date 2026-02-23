from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from src.core.models.config import AppSettings
from src.core.server.openai_compat.auth import create_bearer_auth_dependency
from src.core.server.openai_compat.converters import (
    agent_result_to_openai_response,
    make_stream_chunk,
    openai_request_to_context,
)
from src.core.server.openai_compat.models import (
    ChatCompletionRequest,
    ModelInfo,
    ModelListResponse,
)
from src.core.server.openai_compat.registry import ModelRegistry, RegisteredModel


def create_openai_router(
    registry: ModelRegistry,
    settings: AppSettings,
) -> APIRouter:
    """Create the OpenAI-compatible API router.

    Provides:
      - ``GET  /v1/models``
      - ``POST /v1/chat/completions`` (streaming and non-streaming)
    """
    router = APIRouter(prefix="/v1", tags=["openai-compat"])
    verify_bearer = create_bearer_auth_dependency(settings)

    @router.get("/models", response_model=ModelListResponse)
    async def list_models(
        _token: str = Depends(verify_bearer),
    ) -> ModelListResponse:
        models = registry.list_models()
        return ModelListResponse(
            data=[
                ModelInfo(id=m.model_id, owned_by=m.owned_by)
                for m in models
            ]
        )

    @router.post("/chat/completions")
    async def chat_completions(
        request: ChatCompletionRequest,
        _token: str = Depends(verify_bearer),
    ) -> Any:
        try:
            registered = registry.get(request.model)
        except KeyError:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "message": f"Model '{request.model}' not found",
                        "type": "invalid_request_error",
                        "code": "model_not_found",
                    }
                },
            ) from None

        context = openai_request_to_context(request)
        completion_id = f"chatcmpl-{uuid4().hex[:24]}"
        created = int(time.time())

        if request.stream:
            return _stream_response(registered, context, request.model, completion_id, created)

        try:
            result = await registered.orchestrator.run(context)
        except TimeoutError:
            raise HTTPException(
                status_code=504,
                detail={
                    "error": {
                        "message": "Request timed out",
                        "type": "timeout_error",
                        "code": "timeout",
                    }
                },
            ) from None

        return agent_result_to_openai_response(
            result, model=request.model, completion_id=completion_id
        )

    def _stream_response(
        registered: RegisteredModel,
        context: Any,
        model: str,
        completion_id: str,
        created: int,
    ) -> EventSourceResponse:
        async def event_generator() -> AsyncGenerator[dict[str, str], None]:
            # Initial chunk: role announcement
            first_chunk = make_stream_chunk(
                completion_id, model, created, role="assistant"
            )
            yield {"data": first_chunk.model_dump_json()}

            if registered.streamable_agent is not None:
                async for token in registered.streamable_agent.stream_run(context):
                    chunk = make_stream_chunk(
                        completion_id, model, created, content=token
                    )
                    yield {"data": chunk.model_dump_json()}
            else:
                # Fallback: run non-streaming and emit full response as one chunk
                result = await registered.orchestrator.run(context)
                chunk = make_stream_chunk(
                    completion_id, model, created, content=result.response
                )
                yield {"data": chunk.model_dump_json()}

            # Finish chunk
            final_chunk = make_stream_chunk(
                completion_id, model, created, finish_reason="stop"
            )
            yield {"data": final_chunk.model_dump_json()}

            # OpenAI protocol terminator
            yield {"data": "[DONE]"}

        return EventSourceResponse(event_generator())

    return router
