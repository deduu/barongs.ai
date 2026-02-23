from __future__ import annotations

from src.core.interfaces.agent import Agent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult


class PipelineStrategy:
    """Run agents sequentially; each agent's response becomes
    the next agent's user_message in a new context."""

    async def execute(self, agents: list[Agent], context: AgentContext) -> AgentResult:
        if not agents:
            raise ValueError("PipelineStrategy requires at least one agent")

        current_context = context
        result: AgentResult | None = None

        for agent in agents:
            result = await agent.run(current_context)
            current_context = current_context.model_copy(update={"user_message": result.response})

        assert result is not None
        return result
