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
    ) -> None:
        self._on_task_complete = on_task_complete
        self._on_budget_update = on_budget_update
        self._max_iterations = max_iterations

    async def execute(self, agents: list[Agent], context: AgentContext) -> AgentResult:
        plan_data = context.metadata.get("research_plan", {})
        budget_data = context.metadata.get("research_budget")

        tasks: list[dict[str, Any]] = list(plan_data.get("tasks", []))
        max_iter = plan_data.get("max_iterations", self._max_iterations)

        agent_map: dict[str, Agent] = {a.name: a for a in agents}
        task_statuses: dict[str, str] = {t["task_id"]: "pending" for t in tasks}
        failed_tasks: set[str] = set()
        all_results: list[AgentResult] = []

        for _iteration in range(max_iter):
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

    async def _execute_all_waves(
        self,
        tasks: list[dict[str, Any]],
        task_statuses: dict[str, str],
        failed_tasks: set[str],
        agent_map: dict[str, Agent],
        context: AgentContext,
        budget_data: dict[str, Any] | None,
        all_results: list[AgentResult],
    ) -> bool:
        """Execute waves until no more pending tasks can run. Returns True if any work was done."""
        any_work_done = False

        while True:
            if budget_data and self._is_exhausted(budget_data):
                break

            wave = self._next_ready_wave(tasks, task_statuses, failed_tasks)
            if not wave:
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

                task_context = context.model_copy(
                    update={
                        "user_message": task["query"],
                        "metadata": {
                            **context.metadata,
                            "task_id": task["task_id"],
                            "task_type": task["task_type"],
                            "all_findings": [r.metadata.get("findings", []) for r in all_results],
                        },
                    }
                )
                coros.append(self._run_agent(agent_map[agent_name], task_context))

            if not coros:
                break

            results = await asyncio.gather(*coros, return_exceptions=True)
            any_work_done = True

            for task_id, result in zip(wave_task_ids, results, strict=True):
                if isinstance(result, BaseException):
                    logger.error("Task %s failed: %s", task_id, result)
                    task_statuses[task_id] = "failed"
                    failed_tasks.add(task_id)
                    if self._on_task_complete:
                        await self._on_task_complete(task_id, None, "failed")
                else:
                    task_statuses[task_id] = "completed"
                    all_results.append(result)
                    if self._on_task_complete:
                        await self._on_task_complete(task_id, result, "completed")

                    if budget_data:
                        tokens = sum(result.token_usage.values())
                        budget_data["used_llm_tokens"] = (
                            budget_data.get("used_llm_tokens", 0) + tokens
                        )
                        budget_data["used_api_calls"] = budget_data.get("used_api_calls", 0) + 1
                        if self._on_budget_update:
                            await self._on_budget_update(budget_data)

        return any_work_done

    @staticmethod
    async def _run_agent(agent: Agent, context: AgentContext) -> AgentResult:
        return await agent.run(context)

    @staticmethod
    def _is_exhausted(budget: dict[str, Any]) -> bool:
        exhausted: bool = (
            budget.get("used_llm_tokens", 0) >= budget.get("max_llm_tokens", float("inf"))
            or budget.get("used_api_calls", 0) >= budget.get("max_api_calls", float("inf"))
            or budget.get("used_time_seconds", 0) >= budget.get("max_time_seconds", float("inf"))
        )
        return exhausted

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
        for r in results:
            findings = r.metadata.get("findings", [])
            if isinstance(findings, list):
                all_findings.extend(findings)
            mis_ids = r.metadata.get("misattributed_ids", [])
            if isinstance(mis_ids, list):
                all_misattributed.extend(mis_ids)

        return AgentResult(
            agent_name="research_dag",
            response=combined_response,
            metadata={
                "sources": [r.agent_name for r in results],
                "findings": all_findings,
                "misattributed_ids": all_misattributed,
            },
            token_usage=combined_tokens,
        )
