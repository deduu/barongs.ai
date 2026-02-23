from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ToolCallRecord(BaseModel):
    """Record of a single tool invocation."""

    tool_name: str
    input_params: dict[str, Any]
    output: Any
    duration_ms: float
    success: bool


class ToolResult(BaseModel):
    """Result returned from Tool.execute()."""

    tool_name: str
    output: Any
    success: bool = True
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Result returned from Agent.run()."""

    request_id: UUID = Field(default_factory=uuid4)
    agent_name: str
    response: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    token_usage: dict[str, int] = Field(default_factory=dict)
    duration_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
