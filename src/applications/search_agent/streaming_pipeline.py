from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from src.applications.search_agent.agents.synthesizer import SynthesizerAgent
from src.core.interfaces.agent import Agent
from src.core.models.context import AgentContext


class StreamableSearchPipeline:
    """Wraps the search pipeline for OpenAI-compatible streaming.

    Runs the web researcher (non-streaming) to gather sources, then streams
    the synthesizer's response token by token.
    """

    def __init__(
        self,
        web_researcher: Agent,
        synthesizer: SynthesizerAgent,
    ) -> None:
        self._web_researcher = web_researcher
        self._synthesizer = synthesizer

    async def stream_run(self, context: AgentContext) -> AsyncIterator[str]:
        # Phase 1: research (non-streaming)
        research_context = AgentContext(
            user_message=context.user_message,
            conversation_history=context.conversation_history,
            metadata={**context.metadata, "refined_queries": [context.user_message]},
        )
        research_result = await self._web_researcher.run(research_context)
        sources: list[dict[str, Any]] = research_result.metadata.get("sources", [])

        # Phase 2: synthesize (streaming)
        synth_context = AgentContext(
            user_message=context.user_message,
            conversation_history=context.conversation_history,
            metadata={**context.metadata, "sources": sources},
        )
        async for token in self._synthesizer.stream_run(synth_context):
            yield token
