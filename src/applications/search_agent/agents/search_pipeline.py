from __future__ import annotations

from src.core.interfaces.agent import Agent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult


class SearchPipelineAgent(Agent):
    """Composite agent that orchestrates the full search pipeline.

    Routes between search path (QueryAnalyzer → WebResearcher → Synthesizer)
    and direct answer path based on query classification.

    From the Orchestrator's perspective, this is a single agent.
    """

    def __init__(
        self,
        query_analyzer: Agent,
        web_researcher: Agent,
        synthesizer: Agent,
        direct_answerer: Agent,
    ) -> None:
        self._query_analyzer = query_analyzer
        self._web_researcher = web_researcher
        self._synthesizer = synthesizer
        self._direct_answerer = direct_answerer

    @property
    def name(self) -> str:
        return "search_pipeline"

    @property
    def description(self) -> str:
        return "Full search pipeline: analyze → research → synthesize (or direct answer)."

    async def run(self, context: AgentContext) -> AgentResult:
        # Always search with the original query (skip QueryAnalyzer LLM call
        # to reduce latency — like Perplexity/Grok do).
        research_context = context.model_copy(
            update={"metadata": {**context.metadata, "refined_queries": [context.user_message]}}
        )
        research_result = await self._web_researcher.run(research_context)

        sources = research_result.metadata.get("sources", [])
        synth_context = context.model_copy(
            update={"metadata": {**context.metadata, "sources": sources}}
        )
        synth_result = await self._synthesizer.run(synth_context)

        return AgentResult(
            agent_name=self.name,
            response=synth_result.response,
            metadata={
                "sources": sources,
                "query_type": "search",
                "refined_queries": [context.user_message],
            },
            token_usage=synth_result.token_usage,
        )
