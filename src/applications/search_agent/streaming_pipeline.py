from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from src.applications.search_agent.agents.synthesizer import SynthesizerAgent
from src.core.interfaces.agent import Agent
from src.core.interfaces.orchestrator import Orchestrator
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult
from src.core.orchestrator.strategies.single_agent import SingleAgentStrategy


class StreamableSearchPipeline:
    """Wraps the search pipeline for OpenAI-compatible streaming.

    Runs the web researcher via an Orchestrator (non-streaming) to gather
    sources, then streams the synthesizer's response token by token.
    """

    def __init__(
        self,
        web_researcher: Agent,
        synthesizer: SynthesizerAgent,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._researcher_orchestrator = Orchestrator(
            strategy=SingleAgentStrategy(),
            agents=[web_researcher],
            timeout_seconds=timeout_seconds,
        )
        self._synthesizer = synthesizer

    async def research(self, context: AgentContext) -> AgentResult:
        """Run the web researcher and return the result with sources."""
        research_context = AgentContext(
            user_message=context.user_message,
            conversation_history=context.conversation_history,
            metadata={**context.metadata, "refined_queries": [context.user_message]},
        )
        return await self._researcher_orchestrator.run(research_context)

    async def stream_synthesize(
        self, context: AgentContext, sources: list[dict[str, Any]]
    ) -> AsyncIterator[str]:
        """Stream synthesis tokens given sources."""
        synth_context = AgentContext(
            user_message=context.user_message,
            conversation_history=context.conversation_history,
            metadata={**context.metadata, "sources": sources},
        )
        async for token in self._synthesizer.stream_run(synth_context):
            yield token

    async def stream_run(self, context: AgentContext) -> AsyncIterator[str]:
        """Full pipeline: research then stream synthesis."""
        result = await self.research(context)
        sources: list[dict[str, Any]] = result.metadata.get("sources", [])
        async for token in self.stream_synthesize(context, sources):
            yield token
