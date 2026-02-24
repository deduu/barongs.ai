from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.models.context import AgentContext
from src.core.models.results import AgentResult


class Agent(ABC):
    """Base class for all agents in the barongsai framework.

    Every agent must implement the async `run` method.
    Agents receive a fully-populated AgentContext and return an AgentResult.
    Timeout enforcement is handled by the orchestrator, not by the agent itself.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description, used by the Router strategy."""
        return ""

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the agent's logic.

        Args:
            context: Immutable context containing the user message,
                     conversation history, available tools, and metadata.

        Returns:
            AgentResult containing the response, any tool calls made,
            metadata, and token information.
        """
        ...

    async def setup(self) -> None:  # noqa: B027
        """Optional lifecycle hook called once before first run."""

    async def teardown(self) -> None:  # noqa: B027
        """Optional lifecycle hook for cleanup."""
