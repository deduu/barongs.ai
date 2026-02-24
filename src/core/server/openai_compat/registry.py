from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from src.core.interfaces.orchestrator import Orchestrator
from src.core.models.context import AgentContext


@runtime_checkable
class StreamableAgent(Protocol):
    """Protocol for agents that support token-level streaming."""

    def stream_run(self, context: AgentContext) -> AsyncIterator[str]: ...


@dataclass
class RegisteredModel:
    """A Barongsai agent/orchestrator registered as an OpenAI-compatible model."""

    model_id: str
    orchestrator: Orchestrator
    owned_by: str = "barongsai"
    description: str = ""
    streamable_agent: StreamableAgent | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelRegistry:
    """Maps OpenAI model names to Barongsai orchestrator instances."""

    def __init__(self) -> None:
        self._models: dict[str, RegisteredModel] = {}

    def register(
        self,
        model_id: str,
        orchestrator: Orchestrator,
        *,
        owned_by: str = "barongsai",
        description: str = "",
        streamable_agent: StreamableAgent | None = None,
    ) -> None:
        self._models[model_id] = RegisteredModel(
            model_id=model_id,
            orchestrator=orchestrator,
            owned_by=owned_by,
            description=description,
            streamable_agent=streamable_agent,
        )

    def get(self, model_id: str) -> RegisteredModel:
        if model_id not in self._models:
            available = ", ".join(self._models) or "(none)"
            msg = f"Model '{model_id}' not found. Available: {available}"
            raise KeyError(msg)
        return self._models[model_id]

    def list_models(self) -> list[RegisteredModel]:
        return list(self._models.values())
