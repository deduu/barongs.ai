from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from src.applications.deep_search.entity_grounding import (
    build_entity_grounding,
    extract_urls,
    fetch_primary_sources,
    grounding_requires_disambiguation,
)
from src.applications.deep_search.query_utils import build_query_variants, normalize_research_query
from src.applications.deep_search.models.outline import OutlineSection, ResearchTask
from src.applications.deep_search.models.streaming import DeepSearchEventType
from src.applications.deep_search.session_store import SessionStore
from src.core.interfaces.agent import Agent
from src.core.interfaces.orchestrator import Orchestrator
from src.core.interfaces.tool import Tool
from src.core.llm.base import LLMProvider
from src.core.models.context import AgentContext
from src.core.orchestrator.strategies.single_agent import SingleAgentStrategy

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
        timeout_seconds: float = 300.0,
        research_max_llm_tokens: int = 100_000,
        research_max_api_calls: int = 50,
        research_max_time_seconds: float = 300.0,
        timeout_grace_seconds: float = 10.0,
    ) -> None:
        self._planner_orchestrator = Orchestrator(
            strategy=SingleAgentStrategy(),
            agents=[planner],
            timeout_seconds=timeout_seconds,
        )
        self._synthesizer = synthesizer
        self._strategy = strategy
        self._agents = agents
        self._dag_orchestrator = Orchestrator(
            strategy=strategy,
            agents=agents,
            timeout_seconds=timeout_seconds,
        )
        self._content_fetcher = content_fetcher
        self._llm = llm_provider
        self._model = model
        self._session_store = session_store
        self._outline_timeout = outline_timeout
        self._default_timeout_seconds = timeout_seconds
        self._research_max_llm_tokens = research_max_llm_tokens
        self._research_max_api_calls = research_max_api_calls
        self._research_max_time_seconds = research_max_time_seconds
        self._timeout_grace_seconds = timeout_grace_seconds

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

            session_id = context.session_id or ""
            if (
                grounding_requires_disambiguation(entity_grounding_data)
                and self._session_store
                and session_id
            ):
                clarification_prompt = str(
                    entity_grounding_data.get(
                        "clarification_prompt",
                        "Clarify which specific entity you mean before research continues.",
                    )
                )
                session = self._session_store.create(session_id)
                yield self._event(
                    DeepSearchEventType.DISAMBIGUATION_REQUIRED,
                    {
                        "session_id": session_id,
                        "entity_name": entity_grounding_data.get("name", ""),
                        "message": clarification_prompt,
                    },
                )

                user_response = await session.wait_for_confirmation(
                    timeout=self._outline_timeout,
                )
                self._session_store.remove(session_id)

                if user_response is None:
                    yield self._event(
                        DeepSearchEventType.ERROR,
                        {"error": "Disambiguation confirmation timed out"},
                    )
                    return

                clarification = str(user_response.get("clarification", "")).strip()
                if not clarification:
                    yield self._event(
                        DeepSearchEventType.ERROR,
                        {"error": "A clarification is required before research can continue."},
                    )
                    return

                clarified_query = (
                    f"{context.user_message}\nClarification: {clarification}"
                )
                if self._llm:
                    grounding = await build_entity_grounding(
                        clarified_query,
                        [],
                        self._llm,
                        self._model,
                    )
                    entity_grounding_data = grounding.model_dump()

                enriched_context = context.model_copy(
                    update={
                        "user_message": clarified_query,
                        "metadata": {
                            **context.metadata,
                            "entity_grounding": entity_grounding_data,
                            "user_provided_urls": user_urls,
                            "disambiguation_clarification": clarification,
                        },
                    }
                )
                yield self._event(
                    DeepSearchEventType.DISAMBIGUATION_CONFIRMED,
                    {
                        "session_id": session_id,
                        "message": "Clarification received, continuing research.",
                    },
                )

            # Phase 1: Planning
            yield self._event(DeepSearchEventType.PLANNING, {"status": "creating research plan"})

            plan_timeout = self._request_max_time_seconds(context.metadata)
            plan_result = await self._planner_orchestrator.run(
                enriched_context,
                timeout_seconds=plan_timeout,
            )
            plan = plan_result.metadata.get("research_plan", {})
            plan = self._ensure_academic_coverage(
                plan,
                original_query=context.user_message,
                enabled=bool(context.metadata.get("enable_academic_search", True)),
            )
            requested_max_iterations = context.metadata.get("max_iterations")
            if isinstance(requested_max_iterations, int) and requested_max_iterations > 0:
                plan["max_iterations"] = requested_max_iterations

            yield self._event(
                DeepSearchEventType.PLANNING,
                {
                    "status": "plan created",
                    "task_count": len(plan.get("tasks", [])),
                },
            )

            # Interactive outline: pause for user editing if requested
            interactive = context.metadata.get("interactive_outline", False)
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
            attempted_sources: list[dict[str, Any]] = []
            if plan.get("tasks"):
                yield self._event(DeepSearchEventType.RESEARCHING, {"status": "starting research"})
                logger.info("Deep search research phase started with %s tasks", len(plan.get("tasks", [])))

                progress_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

                async def _task_progress_callback(payload: dict[str, Any]) -> None:
                    await progress_queue.put(
                        self._event(
                            DeepSearchEventType.RESEARCHING,
                            {
                                "status": (
                                    f"{payload.get('status', 'update')}: "
                                    f"{payload.get('agent_name', payload.get('task_id', 'task'))}"
                                ),
                                **payload,
                            },
                        )
                    )

                async def _budget_progress_callback(payload: dict[str, Any]) -> None:
                    await progress_queue.put(
                        self._event(DeepSearchEventType.BUDGET_UPDATE, payload)
                    )

                research_context = enriched_context.model_copy(
                    update={
                        "metadata": {
                            **enriched_context.metadata,
                            "research_plan": plan,
                            "research_budget": self._build_research_budget(
                                enriched_context.metadata,
                            ),
                            "_task_progress_callback": _task_progress_callback,
                            "_budget_progress_callback": _budget_progress_callback,
                        },
                    }
                )
                dag_budget = research_context.metadata.get("research_budget", {})
                dag_max_time = float(
                    dag_budget.get(
                        "max_time_seconds",
                        self._request_max_time_seconds(enriched_context.metadata),
                    )
                )
                dag_timeout = dag_max_time + self._timeout_grace_seconds

                # Run the DAG as a background task and emit heartbeat events
                # while waiting so the frontend doesn't appear hung.
                dag_task = asyncio.create_task(
                    self._dag_orchestrator.run(
                        research_context,
                        timeout_seconds=dag_timeout,
                    )
                )
                elapsed = 0
                while True:
                    done, _ = await asyncio.wait({dag_task}, timeout=5.0)
                    while not progress_queue.empty():
                        queued_event = await progress_queue.get()
                        yield queued_event
                    if done:
                        break
                    elapsed += 5
                    remaining = max(0.0, dag_max_time - elapsed)
                    yield self._event(
                        DeepSearchEventType.RESEARCHING,
                        {
                            "status": f"researching ({elapsed}s elapsed)",
                            "remaining_time_seconds": round(remaining, 1),
                            "active_task_count": len(plan.get("tasks", [])),
                        },
                    )

                dag_result = await dag_task
                while not progress_queue.empty():
                    queued_event = await progress_queue.get()
                    yield queued_event
                findings: list[dict[str, Any]] = dag_result.metadata.get("findings", [])
                misattributed_ids = dag_result.metadata.get("misattributed_ids", [])
                attempted_sources = dag_result.metadata.get("attempted_sources", [])

                for finding in findings:
                    yield self._event(DeepSearchEventType.FINDING, {"finding": finding})

                yield self._event(
                    DeepSearchEventType.RESEARCHING,
                    {
                        "status": "research complete",
                        "finding_count": len(findings),
                    },
                )

                # Reflection phase: surface before synthesis
                yield self._event(
                    DeepSearchEventType.REFLECTING,
                    {"status": "reviewing and filtering findings"},
                )
            else:
                findings = []
                attempted_sources = []

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
                        "attempted_sources": attempted_sources,
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

        except asyncio.TimeoutError:
            logger.error("Deep search pipeline timeout", exc_info=True)
            yield self._event(
                DeepSearchEventType.ERROR,
                {
                    "error": (
                        "Deep search timed out before completion. "
                        "Increase max_time_seconds or narrow the query scope."
                    ),
                },
            )
        except Exception as exc:
            logger.error("Deep search pipeline error: %s", exc, exc_info=True)
            yield self._event(DeepSearchEventType.ERROR, {"error": str(exc)})

    @staticmethod
    def _event(event_type: DeepSearchEventType, data: dict[str, Any]) -> dict[str, Any]:
        return {"event": event_type, "data": data}

    @staticmethod
    def _has_academic_task(tasks: list[dict[str, Any]]) -> bool:
        for task in tasks:
            if task.get("task_type") == "secondary_academic":
                return True
            if task.get("agent_name") == "academic_researcher":
                return True
        return False

    @staticmethod
    def _next_task_id(tasks: list[dict[str, Any]]) -> str:
        taken = {str(task.get("task_id", "")) for task in tasks}
        index = 1
        while f"t{index}" in taken:
            index += 1
        return f"t{index}"

    def _ensure_academic_coverage(
        self,
        plan: dict[str, Any],
        *,
        original_query: str,
        enabled: bool,
    ) -> dict[str, Any]:
        if not enabled:
            return plan
        if not any(agent.name == "academic_researcher" for agent in self._agents):
            return plan
        tasks = plan.get("tasks", [])
        if not isinstance(tasks, list):
            return plan
        if self._has_academic_task(tasks):
            return plan

        normalized_query = normalize_research_query(original_query)
        query_variants = build_query_variants(original_query)
        academic_query = query_variants[0] if query_variants else normalized_query

        augmented_tasks = list(tasks)
        augmented_tasks.append(
            {
                "task_id": self._next_task_id(augmented_tasks),
                "query": academic_query,
                "task_type": "secondary_academic",
                "depends_on": [],
                "agent_name": "academic_researcher",
            }
        )
        updated_plan = dict(plan)
        updated_plan["tasks"] = augmented_tasks
        return updated_plan

    def _request_max_time_seconds(self, metadata: dict[str, Any]) -> float:
        requested = metadata.get("max_time_seconds")
        if isinstance(requested, (int, float)) and requested > 0:
            return float(requested)
        return self._default_timeout_seconds

    def _build_research_budget(self, metadata: dict[str, Any]) -> dict[str, Any]:
        requested_max_time = metadata.get("max_time_seconds")
        max_time_seconds = (
            float(requested_max_time)
            if isinstance(requested_max_time, (int, float)) and requested_max_time > 0
            else self._research_max_time_seconds
        )
        return {
            "max_llm_tokens": self._research_max_llm_tokens,
            "max_api_calls": self._research_max_api_calls,
            "max_time_seconds": max_time_seconds,
            "used_llm_tokens": 0,
            "used_api_calls": 0,
            "used_time_seconds": 0.0,
        }
