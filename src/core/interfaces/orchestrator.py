from __future__ import annotations

import asyncio
from typing import Protocol, runtime_checkable

from src.core.interfaces.agent import Agent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult


@runtime_checkable
class OrchestratorStrategy(Protocol):
    """Protocol that all orchestration strategies must satisfy.

    Using Protocol (structural typing) rather than ABC so third-party
    strategies don't need to inherit from our base.
    """

    async def execute(
        self,
        agents: list[Agent],
        context: AgentContext,
    ) -> AgentResult: ...


class Orchestrator:
    """Main orchestrator that delegates to a pluggable strategy.

    The Orchestrator owns the agent registry, applies timeouts,
    and invokes the strategy.
    """

    def __init__(
        self,
        strategy: OrchestratorStrategy,
        agents: list[Agent],
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._strategy = strategy
        self._agents = agents
        self._timeout_seconds = timeout_seconds

    @property
    def strategy(self) -> OrchestratorStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, new_strategy: OrchestratorStrategy) -> None:
        self._strategy = new_strategy

    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the current strategy with timeout enforcement."""
        return await asyncio.wait_for(
            self._strategy.execute(self._agents, context),
            timeout=self._timeout_seconds,
        )
