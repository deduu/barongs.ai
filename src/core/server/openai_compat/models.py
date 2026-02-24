from __future__ import annotations

import time
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class OpenAIChatMessage(BaseModel):
    """A single message in OpenAI chat format."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    model: str
    messages: list[OpenAIChatMessage]
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    stop: str | list[str] | None = None
    n: int = 1
    user: str | None = None


class ChatCompletionChoice(BaseModel):
    """A single choice in a non-streaming chat completion response."""

    index: int = 0
    message: OpenAIChatMessage
    finish_reason: Literal["stop", "length", "tool_calls"] | None = "stop"


class UsageInfo(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""

    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid4().hex[:24]}")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[ChatCompletionChoice]
    usage: UsageInfo = Field(default_factory=UsageInfo)


class ChatCompletionChunkDelta(BaseModel):
    """Delta content in a streaming chunk."""

    role: str | None = None
    content: str | None = None


class ChatCompletionChunkChoice(BaseModel):
    """A single choice in a streaming chunk."""

    index: int = 0
    delta: ChatCompletionChunkDelta
    finish_reason: Literal["stop", "length", "tool_calls"] | None = None


class ChatCompletionChunk(BaseModel):
    """A single Server-Sent Event chunk for streaming responses."""

    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChatCompletionChunkChoice]


class ModelInfo(BaseModel):
    """A single model entry returned by /v1/models."""

    id: str
    object: Literal["model"] = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "barongsai"


class ModelListResponse(BaseModel):
    """Response for GET /v1/models."""

    object: Literal["list"] = "list"
    data: list[ModelInfo]


class OpenAIErrorDetail(BaseModel):
    """Inner error detail in OpenAI error format."""

    message: str
    type: str
    param: str | None = None
    code: str | None = None


class OpenAIErrorResponse(BaseModel):
    """OpenAI-compatible error response."""

    error: OpenAIErrorDetail
