from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from src.core.models.context import AgentContext
from src.core.models.results import AgentResult
from src.core.server.openai_compat.models import (
    ChatCompletionChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionChunkDelta,
    ChatCompletionRequest,
    ChatCompletionResponse,
    OpenAIChatMessage,
    UsageInfo,
)


def openai_request_to_context(request: ChatCompletionRequest) -> AgentContext:
    """Convert an OpenAI ChatCompletionRequest to a Pormetheus AgentContext.

    The last user message becomes ``user_message``; all other messages go
    into ``conversation_history``.
    """
    last_user_idx = -1
    for i in range(len(request.messages) - 1, -1, -1):
        if request.messages[i].role == "user":
            last_user_idx = i
            break

    if last_user_idx >= 0:
        user_message = request.messages[last_user_idx].content or ""
        conversation_history: list[dict[str, Any]] = [
            {"role": m.role, "content": m.content or ""}
            for j, m in enumerate(request.messages)
            if j != last_user_idx
        ]
    else:
        user_message = ""
        conversation_history = [
            {"role": m.role, "content": m.content or ""}
            for m in request.messages
        ]

    return AgentContext(
        user_message=user_message,
        conversation_history=conversation_history,
        metadata={
            "openai_model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": request.stream,
        },
    )


def agent_result_to_openai_response(
    result: AgentResult,
    model: str,
    completion_id: str | None = None,
) -> ChatCompletionResponse:
    """Convert an AgentResult to an OpenAI ChatCompletionResponse."""
    cid = completion_id or f"chatcmpl-{uuid4().hex[:24]}"

    return ChatCompletionResponse(
        id=cid,
        model=model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=OpenAIChatMessage(role="assistant", content=result.response),
                finish_reason="stop",
            )
        ],
        usage=UsageInfo(
            prompt_tokens=result.token_usage.get("prompt_tokens", 0),
            completion_tokens=result.token_usage.get("completion_tokens", 0),
            total_tokens=result.token_usage.get("total_tokens", 0),
        ),
    )


def make_stream_chunk(
    completion_id: str,
    model: str,
    created: int,
    *,
    role: str | None = None,
    content: str | None = None,
    finish_reason: Literal["stop", "length", "tool_calls"] | None = None,
) -> ChatCompletionChunk:
    """Build a single SSE chunk in OpenAI streaming format."""
    return ChatCompletionChunk(
        id=completion_id,
        created=created,
        model=model,
        choices=[
            ChatCompletionChunkChoice(
                index=0,
                delta=ChatCompletionChunkDelta(role=role, content=content),
                finish_reason=finish_reason,
            )
        ],
    )
