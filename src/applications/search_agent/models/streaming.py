from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StreamEventType(StrEnum):
    """Types of SSE events during a search response."""

    STATUS = "status"
    SOURCE = "source"
    CHUNK = "chunk"
    DONE = "done"
    ERROR = "error"


class StreamEvent(BaseModel):
    """A single Server-Sent Event for streaming search responses."""

    event: StreamEventType
    data: dict[str, Any] = Field(default_factory=dict)
