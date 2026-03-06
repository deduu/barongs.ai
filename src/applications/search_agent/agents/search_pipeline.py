from __future__ import annotations

from src.core.interfaces.agent import Agent
from src.core.interfaces.orchestrator import Orchestrator
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult
from src.core.orchestrator.strategies.single_agent import SingleAgentStrategy


class SearchPipelineAgent(Agent):
    """Composite agent that orchestrates the full search pipeline.

    Routes between search path (QueryAnalyzer → WebResearcher → Synthesizer)
    and direct answer path based on query classification.

    All agent execution is delegated through Orchestrator instances.
    From the top-level Orchestrator's perspective, this is a single agent.
    """

    def __init__(
        self,
        query_analyzer: Agent,
        search_path: Agent,
        direct_answerer: Agent,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._analyzer_orchestrator = Orchestrator(
            strategy=SingleAgentStrategy(),
            agents=[query_analyzer],
            timeout_seconds=timeout_seconds,
        )
        self._search_path = search_path  # SearchPathAgent (has internal orchestrator)
        self._direct_orchestrator = Orchestrator(
            strategy=SingleAgentStrategy(),
            agents=[direct_answerer],
            timeout_seconds=timeout_seconds,
        )

    @property
    def name(self) -> str:
        return "search_pipeline"

    @property
    def description(self) -> str:
        return "Full search pipeline: analyze → research → synthesize (or direct answer)."

    async def run(self, context: AgentContext) -> AgentResult:
        # Step 1: Analyze and refine the query for better search results
        analysis_result = await self._analyzer_orchestrator.run(context)
        query_type: str = analysis_result.metadata.get("query_type", "search")
        refined_queries: list[str] = analysis_result.metadata.get(
            "refined_queries", [context.user_message]
        )

        # Direct answer path — no web search needed
        if query_type == "direct":
            direct_result = await self._direct_orchestrator.run(context)
            return AgentResult(
                agent_name=self.name,
                response=direct_result.response,
                metadata={"query_type": "direct", "refined_queries": refined_queries},
                token_usage=direct_result.token_usage,
            )

        # Step 2: Search path — research with refined queries
        research_context = context.model_copy(
            update={"metadata": {**context.metadata, "refined_queries": refined_queries}}
        )
        search_result = await self._search_path.run(research_context)

        return AgentResult(
            agent_name=self.name,
            response=search_result.response,
            metadata={
                "sources": search_result.metadata.get("sources", []),
                "query_type": query_type,
                "refined_queries": refined_queries,
            },
            token_usage=search_result.token_usage,
        )
