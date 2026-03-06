from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from src.core.interfaces.agent import Agent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult

logger = logging.getLogger(__name__)

TaskCallback = Callable[[str, AgentResult | None, str], Awaitable[None]]
BudgetCallback = Callable[[dict[str, Any]], Awaitable[None]]


class ResearchDAGStrategy:
    """Execute a DAG of research tasks with dependency awareness, budget tracking, and reflection loops.

    Reads ``research_plan`` and ``research_budget`` from ``context.metadata``.
    Tasks are topologically sorted into waves of independent work and run via ``asyncio.gather``.
    """

    def __init__(
        self,
        *,
        on_task_complete: TaskCallback | None = None,
        on_budget_update: BudgetCallback | None = None,
        max_iterations: int = 3,
        per_agent_timeout: float = 120.0,
    ) -> None:
        self._on_task_complete = on_task_complete
        self._on_budget_update = on_budget_update
        self._max_iterations = max_iterations
        self._per_agent_timeout = per_agent_timeout

    async def execute(self, agents: list[Agent], context: AgentContext) -> AgentResult:
        plan_data = context.metadata.get("research_plan", {})
        budget_data = context.metadata.get("research_budget")
        if not isinstance(budget_data, dict):
            budget_data = None

        tasks: list[dict[str, Any]] = list(plan_data.get("tasks", []))
        max_iter = plan_data.get("max_iterations", self._max_iterations)

        agent_map: dict[str, Agent] = {a.name: a for a in agents}
        task_statuses: dict[str, str] = {t["task_id"]: "pending" for t in tasks}
        failed_tasks: set[str] = set()
        all_results: list[AgentResult] = []
        loop = asyncio.get_running_loop()
        run_started = loop.time()
        initial_used_time = (
            float(budget_data.get("used_time_seconds", 0.0))
            if budget_data
            else 0.0
        )

        for _iteration in range(max_iter):
            self._update_used_time(
                budget_data,
                run_started=run_started,
                initial_used_time=initial_used_time,
            )
            if budget_data and self._is_exhausted(budget_data):
                logger.info("Budget exhausted, stopping execution")
                break

            # Execute all available waves in this iteration
            made_progress = await self._execute_all_waves(
                tasks,
                task_statuses,
                failed_tasks,
                agent_map,
                context,
                budget_data,
                all_results,
                run_started,
                initial_used_time,
            )

            if not made_progress:
                break

            # Check for reflection results with new tasks
            new_tasks_added = False
            for result in all_results:
                new_tasks_raw = result.metadata.get("new_tasks", [])
                for nt in new_tasks_raw:
                    if nt.get("task_id") not in task_statuses:
                        tasks.append(nt)
                        task_statuses[nt["task_id"]] = "pending"
                        new_tasks_added = True

            if not new_tasks_added:
                break

        return self._merge_results(all_results)

    @staticmethod
    async def _emit_context_task_progress(
        context: AgentContext,
        payload: dict[str, Any],
    ) -> None:
        callback = context.metadata.get("_task_progress_callback")
        if callable(callback):
            await callback(payload)

    @staticmethod
    async def _emit_context_budget_update(
        context: AgentContext,
        payload: dict[str, Any],
    ) -> None:
        callback = context.metadata.get("_budget_progress_callback")
        if callable(callback):
            await callback(payload)

    async def _execute_all_waves(
        self,
        tasks: list[dict[str, Any]],
        task_statuses: dict[str, str],
        failed_tasks: set[str],
        agent_map: dict[str, Agent],
        context: AgentContext,
        budget_data: dict[str, Any] | None,
        all_results: list[AgentResult],
        run_started: float,
        initial_used_time: float,
    ) -> bool:
        """Execute waves until no more pending tasks can run. Returns True if any work was done."""
        any_work_done = False

        while True:
            self._update_used_time(
                budget_data,
                run_started=run_started,
                initial_used_time=initial_used_time,
            )
            if budget_data and self._is_exhausted(budget_data):
                break

            wave = self._next_ready_wave(tasks, task_statuses, failed_tasks)
            if not wave:
                break

            remaining_time = self._remaining_time_seconds(budget_data)
            if remaining_time is not None and remaining_time <= 0:
                break

            coros = []
            wave_task_ids: list[str] = []
            for task in wave:
                agent_name = task.get("agent_name")
                if not agent_name or agent_name not in agent_map:
                    task_statuses[task["task_id"]] = "skipped"
                    continue

                task_statuses[task["task_id"]] = "running"
                wave_task_ids.append(task["task_id"])
                logger.info(
                    "Research task started: task_id=%s agent=%s query=%s",
                    task["task_id"],
                    agent_name,
                    task.get("query", ""),
                )
                await self._emit_context_task_progress(
                    context,
                    {
                        "task_id": task["task_id"],
                        "status": "running",
                        "agent_name": agent_name,
                        "query": task.get("query", ""),
                    },
                )

                task_context = context.model_copy(
                    update={
                        "user_message": task["query"],
                        "metadata": {
                            **context.metadata,
                            "task_id": task["task_id"],
                            "task_type": task["task_type"],
                            "all_findings": [r.metadata.get("findings", []) for r in all_results],
                            "agent_timeout_seconds": (
                                min(self._per_agent_timeout, remaining_time)
                                if remaining_time is not None
                                else self._per_agent_timeout
                            ),
                        },
                    }
                )
                coros.append(
                    self._run_agent(
                        agent_map[agent_name],
                        task_context,
                        remaining_time=remaining_time,
                    )
                )

            if not coros:
                break

            results = await asyncio.gather(*coros, return_exceptions=True)
            any_work_done = True
            self._update_used_time(
                budget_data,
                run_started=run_started,
                initial_used_time=initial_used_time,
            )

            for task_id, result in zip(wave_task_ids, results, strict=True):
                if isinstance(result, BaseException):
                    logger.error("Task %s failed: %s", task_id, result)
                    task_statuses[task_id] = "failed"
                    failed_tasks.add(task_id)
                    await self._emit_context_task_progress(
                        context,
                        {
                            "task_id": task_id,
                            "status": "failed",
                            "error": str(result),
                        },
                    )
                    if self._on_task_complete:
                        await self._on_task_complete(task_id, None, "failed")
                else:
                    task_statuses[task_id] = "completed"
                    all_results.append(result)
                    findings = result.metadata.get("findings", [])
                    finding_count = len(findings) if isinstance(findings, list) else 0
                    logger.info(
                        "Research task completed: task_id=%s agent=%s findings=%s",
                        task_id,
                        result.agent_name,
                        finding_count,
                    )
                    await self._emit_context_task_progress(
                        context,
                        {
                            "task_id": task_id,
                            "status": "completed",
                            "agent_name": result.agent_name,
                            "response": result.response,
                            "finding_count": finding_count,
                        },
                    )
                    if self._on_task_complete:
                        await self._on_task_complete(task_id, result, "completed")

                    if budget_data:
                        tokens = sum(result.token_usage.values())
                        budget_data["used_llm_tokens"] = (
                            budget_data.get("used_llm_tokens", 0) + tokens
                        )
                        budget_data["used_api_calls"] = budget_data.get("used_api_calls", 0) + 1
                        await self._emit_context_budget_update(context, budget_data.copy())
                        if self._on_budget_update:
                            await self._on_budget_update(budget_data)

        return any_work_done

    async def _run_agent(
        self,
        agent: Agent,
        context: AgentContext,
        *,
        remaining_time: float | None = None,
    ) -> AgentResult:
        effective_timeout = self._per_agent_timeout
        if remaining_time is not None:
            if remaining_time <= 0:
                return AgentResult(
                    agent_name=agent.name,
                    response="Agent skipped due to exhausted time budget.",
                    metadata={"findings": [], "timed_out": True, "budget_exhausted": True},
                )
            effective_timeout = min(self._per_agent_timeout, remaining_time)

        try:
            return await asyncio.wait_for(
                agent.run(context), timeout=effective_timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Agent %s timed out after %.1fs", agent.name, effective_timeout)
            return AgentResult(
                agent_name=agent.name,
                response=f"Agent timed out after {effective_timeout:.1f}s",
                metadata={"findings": [], "timed_out": True, "timeout_seconds": effective_timeout},
            )

    @staticmethod
    def _is_exhausted(budget: dict[str, Any]) -> bool:
        exhausted: bool = (
            budget.get("used_llm_tokens", 0) >= budget.get("max_llm_tokens", float("inf"))
            or budget.get("used_api_calls", 0) >= budget.get("max_api_calls", float("inf"))
            or budget.get("used_time_seconds", 0) >= budget.get("max_time_seconds", float("inf"))
        )
        return exhausted

    @staticmethod
    def _remaining_time_seconds(budget: dict[str, Any] | None) -> float | None:
        if not budget:
            return None
        max_time = float(budget.get("max_time_seconds", float("inf")))
        used_time = float(budget.get("used_time_seconds", 0.0))
        return max_time - used_time

    @staticmethod
    def _update_used_time(
        budget: dict[str, Any] | None,
        *,
        run_started: float,
        initial_used_time: float,
    ) -> None:
        if not budget:
            return
        elapsed = asyncio.get_running_loop().time() - run_started
        budget["used_time_seconds"] = initial_used_time + max(0.0, elapsed)

    @staticmethod
    def _next_ready_wave(
        tasks: list[dict[str, Any]],
        statuses: dict[str, str],
        failed: set[str],
    ) -> list[dict[str, Any]]:
        """Return the next wave of tasks ready to execute."""
        wave: list[dict[str, Any]] = []
        for task in tasks:
            if statuses.get(task["task_id"]) != "pending":
                continue
            deps = task.get("depends_on", [])
            if any(d in failed for d in deps):
                statuses[task["task_id"]] = "skipped"
                continue
            if all(statuses.get(d) == "completed" for d in deps):
                wave.append(task)
        return wave

    @staticmethod
    def _merge_results(results: list[AgentResult]) -> AgentResult:
        if not results:
            return AgentResult(
                agent_name="research_dag",
                response="No results produced.",
                metadata={},
            )

        combined_response = "\n\n".join(r.response for r in results)
        combined_tokens: dict[str, int] = {}
        for r in results:
            for k, v in r.token_usage.items():
                combined_tokens[k] = combined_tokens.get(k, 0) + v

        all_findings: list[Any] = []
        all_misattributed: list[str] = []
        attempted_sources: list[dict[str, Any]] = []
        for r in results:
            findings = r.metadata.get("findings", [])
            if isinstance(findings, list):
                all_findings.extend(findings)
            mis_ids = r.metadata.get("misattributed_ids", [])
            if isinstance(mis_ids, list):
                all_misattributed.extend(mis_ids)
            sources = r.metadata.get("attempted_sources", [])
            if isinstance(sources, list):
                for source in sources:
                    if isinstance(source, dict):
                        attempted_sources.append(source)

        return AgentResult(
            agent_name="research_dag",
            response=combined_response,
            metadata={
                "sources": [r.agent_name for r in results],
                "findings": all_findings,
                "misattributed_ids": all_misattributed,
                "attempted_sources": attempted_sources,
            },
            token_usage=combined_tokens,
        )
