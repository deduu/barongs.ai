from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from src.applications.deep_search.entity_grounding import (
    build_entity_grounding,
    extract_urls,
    fetch_primary_sources,
)
from src.applications.deep_search.models.outline import OutlineSection, ResearchTask
from src.applications.deep_search.models.streaming import DeepSearchEventType
from src.applications.deep_search.session_store import SessionStore
from src.core.interfaces.agent import Agent
from src.core.interfaces.tool import Tool
from src.core.llm.base import LLMProvider
from src.core.models.context import AgentContext

logger = logging.getLogger(__name__)

# Default report outline sections per research mode.
_DEFAULT_SECTIONS: dict[str, list[OutlineSection]] = {
    "general": [
        OutlineSection(heading="Executive Summary", description="Brief overview of key findings"),
        OutlineSection(heading="Key Findings", description="Detailed analysis organized by topic"),
        OutlineSection(heading="Methodology Notes", description="How the research was conducted"),
        OutlineSection(heading="Limitations", description="Gaps and uncertainties that remain"),
    ],
    "academic": [
        OutlineSection(heading="Abstract", description="Concise summary of research question, methods, findings, and implications"),
        OutlineSection(heading="Introduction", description="Background, problem statement, and significance"),
        OutlineSection(heading="Literature Review", description="Survey of prior work and identification of gaps"),
        OutlineSection(heading="Methodology", description="Research methods, data sources, and limitations"),
        OutlineSection(heading="Results", description="Key findings with supporting evidence"),
        OutlineSection(heading="Discussion", description="Interpretation and comparison with existing literature"),
        OutlineSection(heading="Conclusion", description="Summary, contributions, and practical implications"),
        OutlineSection(heading="Future Work", description="Open questions and directions for further research"),
        OutlineSection(heading="References", description="All sources cited"),
    ],
    "consultant": [
        OutlineSection(heading="Executive Summary", description="High-level overview and critical insights"),
        OutlineSection(heading="Situation Assessment", description="Current state, challenges, and market context"),
        OutlineSection(heading="Key Findings", description="Research findings organized by theme"),
        OutlineSection(heading="Strategic Options", description="Alternative courses of action with pros/cons"),
        OutlineSection(heading="Recommendations", description="Prioritized, actionable recommendations"),
        OutlineSection(heading="Implementation Roadmap", description="Phased approach with milestones"),
        OutlineSection(heading="Risk Analysis", description="Key risks and mitigation strategies"),
    ],
}


class StreamableDeepSearchPipeline:
    """Orchestrates deep search with SSE streaming at every phase.

    Uses the planner, DAG strategy, and synthesizer to produce a full
    research report while streaming intermediate events.
    """

    def __init__(
        self,
        planner: Agent,
        synthesizer: Any,  # DeepSynthesizerAgent with stream_run
        strategy: Any,  # ResearchDAGStrategy or OrchestratorStrategy
        agents: list[Agent],
        *,
        content_fetcher: Tool | None = None,
        llm_provider: LLMProvider | None = None,
        model: str = "gpt-4o",
        session_store: SessionStore | None = None,
        outline_timeout: float = 600.0,
    ) -> None:
        self._planner = planner
        self._synthesizer = synthesizer
        self._strategy = strategy
        self._agents = agents
        self._content_fetcher = content_fetcher
        self._llm = llm_provider
        self._model = model
        self._session_store = session_store
        self._outline_timeout = outline_timeout

    async def stream_run(self, context: AgentContext) -> AsyncIterator[dict[str, Any]]:
        try:
            # Phase 0: Extract URLs, fetch primary sources, build entity grounding
            entity_grounding_data: dict[str, Any] = {}
            user_urls = extract_urls(context.user_message)

            if user_urls and self._content_fetcher and self._llm:
                yield self._event(
                    DeepSearchEventType.STATUS,
                    {
                        "status": "fetching user-provided URLs",
                        "url_count": len(user_urls),
                    },
                )
                primary_sources = await fetch_primary_sources(
                    user_urls,
                    self._content_fetcher,
                )
                if primary_sources:
                    grounding = await build_entity_grounding(
                        context.user_message,
                        primary_sources,
                        self._llm,
                        self._model,
                    )
                    entity_grounding_data = grounding.model_dump()
                    yield self._event(
                        DeepSearchEventType.STATUS,
                        {
                            "status": "entity grounded",
                            "entity_name": grounding.name,
                        },
                    )
                else:
                    grounding = await build_entity_grounding(
                        context.user_message,
                        [],
                        self._llm,
                        self._model,
                    )
                    entity_grounding_data = grounding.model_dump()
            elif self._llm:
                grounding = await build_entity_grounding(
                    context.user_message,
                    [],
                    self._llm,
                    self._model,
                )
                entity_grounding_data = grounding.model_dump()

            enriched_context = context.model_copy(
                update={
                    "metadata": {
                        **context.metadata,
                        "entity_grounding": entity_grounding_data,
                        "user_provided_urls": user_urls,
                    },
                }
            )

            # Phase 1: Planning
            yield self._event(DeepSearchEventType.PLANNING, {"status": "creating research plan"})

            plan_result = await self._planner.run(enriched_context)
            plan = plan_result.metadata.get("research_plan", {})

            yield self._event(
                DeepSearchEventType.PLANNING,
                {
                    "status": "plan created",
                    "task_count": len(plan.get("tasks", [])),
                },
            )

            # Interactive outline: pause for user editing if requested
            interactive = context.metadata.get("interactive_outline", False)
            session_id = context.session_id or ""
            if interactive and self._session_store and session_id:
                research_mode = context.metadata.get("research_mode", "general")
                sections = _DEFAULT_SECTIONS.get(research_mode, _DEFAULT_SECTIONS["general"])
                tasks_raw = plan.get("tasks", [])
                research_tasks = [
                    ResearchTask(
                        task_id=t.get("task_id", f"t{i}"),
                        query=t.get("query", ""),
                        task_type=t.get("task_type", "secondary_web"),
                        agent_name=t.get("agent_name", "deep_web_researcher"),
                        depends_on=t.get("depends_on", []),
                    )
                    for i, t in enumerate(tasks_raw)
                ]

                yield self._event(
                    DeepSearchEventType.OUTLINE_READY,
                    {
                        "session_id": session_id,
                        "query": context.user_message,
                        "research_mode": research_mode,
                        "sections": [s.model_dump() for s in sections],
                        "research_tasks": [t.model_dump() for t in research_tasks],
                    },
                )

                session = self._session_store.create(session_id)
                yield self._event(
                    DeepSearchEventType.AWAITING_CONFIRMATION,
                    {"session_id": session_id},
                )

                user_response = await session.wait_for_confirmation(
                    timeout=self._outline_timeout,
                )
                self._session_store.remove(session_id)

                if user_response is None:
                    yield self._event(
                        DeepSearchEventType.ERROR,
                        {"error": "Outline confirmation timed out"},
                    )
                    return

                # Apply user edits
                if user_response.get("sections"):
                    enriched_context = enriched_context.model_copy(
                        update={
                            "metadata": {
                                **enriched_context.metadata,
                                "custom_sections": user_response["sections"],
                            },
                        }
                    )
                if user_response.get("research_tasks"):
                    plan["tasks"] = user_response["research_tasks"]

                yield self._event(
                    DeepSearchEventType.OUTLINE_CONFIRMED,
                    {"session_id": session_id},
                )

            # Phase 2: Research via DAG
            misattributed_ids: list[str] = []
            if plan.get("tasks"):
                yield self._event(DeepSearchEventType.RESEARCHING, {"status": "starting research"})

                research_context = enriched_context.model_copy(
                    update={
                        "metadata": {**enriched_context.metadata, "research_plan": plan},
                    }
                )

                dag_result = await self._strategy.execute(self._agents, research_context)
                findings: list[dict[str, Any]] = dag_result.metadata.get("findings", [])
                misattributed_ids = dag_result.metadata.get("misattributed_ids", [])

                for finding in findings:
                    yield self._event(DeepSearchEventType.FINDING, {"finding": finding})

                yield self._event(
                    DeepSearchEventType.RESEARCHING,
                    {
                        "status": "research complete",
                        "finding_count": len(findings),
                    },
                )
            else:
                findings = []

            # Filter misattributed findings before synthesis
            misattributed_set = set(misattributed_ids)
            relevant_findings = [
                f for f in findings if f.get("finding_id") not in misattributed_set
            ]

            if not relevant_findings and findings:
                yield self._event(
                    DeepSearchEventType.STATUS,
                    {
                        "status": "warning",
                        "message": "All findings were filtered as irrelevant to the target entity.",
                    },
                )

            # Phase 3: Synthesis (streaming)
            yield self._event(DeepSearchEventType.SYNTHESIZING, {"status": "generating report"})

            synth_context = enriched_context.model_copy(
                update={
                    "metadata": {
                        **enriched_context.metadata,
                        "findings": relevant_findings,
                        "misattributed_ids": misattributed_ids,
                    },
                }
            )

            full_response = ""
            async for token in self._synthesizer.stream_run(synth_context):
                full_response += token
                yield self._event(DeepSearchEventType.CHUNK, {"token": token})

            # Done
            yield self._event(
                DeepSearchEventType.DONE,
                {
                    "response": full_response,
                    "finding_count": len(relevant_findings),
                },
            )

        except Exception as exc:
            logger.error("Deep search pipeline error: %s", exc)
            yield self._event(DeepSearchEventType.ERROR, {"error": str(exc)})

    @staticmethod
    def _event(event_type: DeepSearchEventType, data: dict[str, Any]) -> dict[str, Any]:
        return {"event": event_type, "data": data}
