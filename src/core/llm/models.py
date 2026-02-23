from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    """A single message in an LLM conversation."""

    role: str  # "system" | "user" | "assistant"
    content: str


class LLMRequest(BaseModel):
    """Request payload sent to an LLM provider."""

    messages: list[LLMMessage]
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str | None = None
    tools: list[dict[str, Any]] = Field(default_factory=list)


class LLMResponse(BaseModel):
    """Response received from an LLM provider."""

    content: str
    model: str
    usage: dict[str, int] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    finish_reason: str = "stop"
