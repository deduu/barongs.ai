from __future__ import annotations

from collections.abc import Awaitable, Callable

from src.core.interfaces.agent import Agent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult

RoutingFn = Callable[[list[Agent], AgentContext], Awaitable[Agent]]


class RouterStrategy:
    """Select one agent based on a routing function, then run it."""

    def __init__(self, routing_fn: RoutingFn) -> None:
        self._routing_fn = routing_fn

    async def execute(self, agents: list[Agent], context: AgentContext) -> AgentResult:
        selected = await self._routing_fn(agents, context)
        return await selected.run(context)
