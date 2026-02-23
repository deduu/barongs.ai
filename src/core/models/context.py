from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ToolInput(BaseModel):
    """Validated input for a tool invocation."""

    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    request_id: UUID = Field(default_factory=uuid4)


class AgentContext(BaseModel):
    """Immutable context passed to every agent.run() call."""

    request_id: UUID = Field(default_factory=uuid4)
    user_message: str
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    available_tools: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"frozen": True}
