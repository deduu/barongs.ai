from __future__ import annotations

from src.core.interfaces.agent import Agent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult


class SingleAgentStrategy:
    """Run exactly one agent. Uses the first agent in the list."""

    async def execute(self, agents: list[Agent], context: AgentContext) -> AgentResult:
        if not agents:
            raise ValueError("SingleAgentStrategy requires at least one agent")
        return await agents[0].run(context)
