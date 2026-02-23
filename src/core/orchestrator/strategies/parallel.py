from __future__ import annotations

import asyncio
from collections.abc import Callable

from src.core.interfaces.agent import Agent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult

MergeFn = Callable[[list[AgentResult]], AgentResult]


def default_merge(results: list[AgentResult]) -> AgentResult:
    """Default: concatenate responses, merge metadata."""
    combined_response = "\n\n---\n\n".join(r.response for r in results)
    combined_tool_calls = [tc for r in results for tc in r.tool_calls]
    combined_tokens: dict[str, int] = {}
    for r in results:
        for k, v in r.token_usage.items():
            combined_tokens[k] = combined_tokens.get(k, 0) + v

    return AgentResult(
        agent_name="parallel_aggregate",
        response=combined_response,
        tool_calls=combined_tool_calls,
        token_usage=combined_tokens,
        metadata={"sources": [r.agent_name for r in results]},
    )


class ParallelStrategy:
    """Run all agents concurrently and merge results."""

    def __init__(self, merge_fn: MergeFn | None = None) -> None:
        self._merge_fn = merge_fn or default_merge

    async def execute(self, agents: list[Agent], context: AgentContext) -> AgentResult:
        if not agents:
            return self._merge_fn([])
        tasks = [agent.run(context) for agent in agents]
        results = await asyncio.gather(*tasks)
        return self._merge_fn(list(results))
