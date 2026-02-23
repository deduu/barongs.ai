from __future__ import annotations

from src.core.interfaces.agent import Agent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult


class EchoAgent(Agent):
    """Simple demo agent that echoes the user's message."""

    @property
    def name(self) -> str:
        return "echo_agent"

    @property
    def description(self) -> str:
        return "Echoes the user's message back with a prefix."

    async def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            response=f"[Echo] {context.user_message}",
            metadata={"strategy": "echo"},
        )
