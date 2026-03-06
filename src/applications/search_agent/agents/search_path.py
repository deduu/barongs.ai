from __future__ import annotations

from src.core.interfaces.agent import Agent
from src.core.interfaces.orchestrator import Orchestrator
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult
from src.core.orchestrator.strategies.pipeline_metadata import PipelineWithMetadataStrategy


class SearchPathAgent(Agent):
    """Wraps the web research sub-pipeline behind an Orchestrator.

    Pipeline: WebResearcher → Synthesizer (with metadata propagation).
    Sources discovered by the researcher flow into the synthesizer
    via PipelineWithMetadataStrategy.
    """

    def __init__(
        self,
        web_researcher: Agent,
        synthesizer: Agent,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._orchestrator = Orchestrator(
            strategy=PipelineWithMetadataStrategy(),
            agents=[web_researcher, synthesizer],
            timeout_seconds=timeout_seconds,
        )

    @property
    def name(self) -> str:
        return "search_path"

    @property
    def description(self) -> str:
        return "Web research and synthesis pipeline."

    async def run(self, context: AgentContext) -> AgentResult:
        return await self._orchestrator.run(context)
