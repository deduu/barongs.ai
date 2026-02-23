from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    role: Role
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    conversation_id: str
    messages: list[Message] = Field(default_factory=list)

    def add(self, role: Role, content: str) -> Message:
        msg = Message(role=role, content=content)
        self.messages.append(msg)
        return msg
