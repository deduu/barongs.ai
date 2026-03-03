from __future__ import annotations

from unittest.mock import AsyncMock

from src.applications.deep_search.models.research import (
    ResearchBudget,
    ResearchPlan,
    ResearchTask,
    ResearchTaskType,
)
from src.core.interfaces.agent import Agent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult
from src.core.orchestrator.strategies.research_dag import ResearchDAGStrategy


def _make_agent(name: str, response: str = "ok", metadata: dict | None = None) -> Agent:
    """Create a mock agent with given name and response."""
    agent = AsyncMock(spec=Agent)
    agent.name = name
    agent.description = f"Mock {name}"
    agent.run = AsyncMock(return_value=AgentResult(
        agent_name=name,
        response=response,
        metadata=metadata or {},
    ))
    return agent


class TestResearchDAGStrategySingleTask:
    async def test_single_task_execution(self):
        task = ResearchTask(
            task_id="t1",
            query="What is Python?",
            task_type=ResearchTaskType.SECONDARY_WEB,
            agent_name="web_researcher",
        )
        plan = ResearchPlan(original_query="What is Python?", tasks=[task])

        agent = _make_agent("web_researcher")
        strategy = ResearchDAGStrategy()

        context = AgentContext(
            user_message="What is Python?",
            metadata={"research_plan": plan.model_dump()},
        )
        result = await strategy.execute([agent], context)

        assert agent.run.called
        assert result.agent_name == "research_dag"


class TestResearchDAGStrategyParallel:
    async def test_parallel_independent_tasks(self):
        tasks = [
            ResearchTask(
                task_id="t1",
                query="Topic A",
                task_type=ResearchTaskType.SECONDARY_WEB,
                agent_name="web_researcher",
            ),
            ResearchTask(
                task_id="t2",
                query="Topic B",
                task_type=ResearchTaskType.SECONDARY_ACADEMIC,
                agent_name="academic_researcher",
            ),
        ]
        plan = ResearchPlan(original_query="test", tasks=tasks)

        web_agent = _make_agent("web_researcher", metadata={"findings": [{"id": "f1"}]})
        acad_agent = _make_agent("academic_researcher", metadata={"findings": [{"id": "f2"}]})

        strategy = ResearchDAGStrategy()
        context = AgentContext(
            user_message="test",
            metadata={"research_plan": plan.model_dump()},
        )
        await strategy.execute([web_agent, acad_agent], context)

        assert web_agent.run.called
        assert acad_agent.run.called


class TestResearchDAGStrategySequential:
    async def test_sequential_dependencies(self):
        """A -> B -> C must run in order."""
        tasks = [
            ResearchTask(
                task_id="t1", query="A", task_type=ResearchTaskType.SECONDARY_WEB,
                agent_name="agent_a",
            ),
            ResearchTask(
                task_id="t2", query="B", task_type=ResearchTaskType.FACT_CHECK,
                agent_name="agent_b", depends_on=["t1"],
            ),
            ResearchTask(
                task_id="t3", query="C", task_type=ResearchTaskType.REFLECTION,
                agent_name="agent_c", depends_on=["t2"],
            ),
        ]
        plan = ResearchPlan(original_query="test", tasks=tasks)

        call_order: list[str] = []

        async def make_run(name: str):
            async def run(ctx: AgentContext) -> AgentResult:
                call_order.append(name)
                return AgentResult(agent_name=name, response="ok")
            return run

        agents = []
        for name in ["agent_a", "agent_b", "agent_c"]:
            agent = AsyncMock(spec=Agent)
            agent.name = name
            agent.run = AsyncMock(side_effect=lambda ctx, n=name: (
                call_order.append(n) or AgentResult(agent_name=n, response="ok")
            ))
            agents.append(agent)

        strategy = ResearchDAGStrategy()
        context = AgentContext(
            user_message="test",
            metadata={"research_plan": plan.model_dump()},
        )
        await strategy.execute(agents, context)

        assert call_order == ["agent_a", "agent_b", "agent_c"]


class TestResearchDAGStrategyDiamond:
    async def test_diamond_dependency(self):
        """A -> B, A -> C, B -> D, C -> D."""
        tasks = [
            ResearchTask(
                task_id="t1", query="A", task_type=ResearchTaskType.SECONDARY_WEB,
                agent_name="agent_a",
            ),
            ResearchTask(
                task_id="t2", query="B", task_type=ResearchTaskType.SECONDARY_WEB,
                agent_name="agent_b", depends_on=["t1"],
            ),
            ResearchTask(
                task_id="t3", query="C", task_type=ResearchTaskType.SECONDARY_ACADEMIC,
                agent_name="agent_c", depends_on=["t1"],
            ),
            ResearchTask(
                task_id="t4", query="D", task_type=ResearchTaskType.FACT_CHECK,
                agent_name="agent_d", depends_on=["t2", "t3"],
            ),
        ]
        plan = ResearchPlan(original_query="test", tasks=tasks)

        agents = [_make_agent(f"agent_{x}") for x in "abcd"]
        strategy = ResearchDAGStrategy()
        context = AgentContext(
            user_message="test",
            metadata={"research_plan": plan.model_dump()},
        )
        await strategy.execute(agents, context)

        # All agents should have been called
        for agent in agents:
            assert agent.run.called


class TestResearchDAGStrategyBudget:
    async def test_budget_exhaustion_stops_execution(self):
        tasks = [
            ResearchTask(
                task_id="t1", query="A", task_type=ResearchTaskType.SECONDARY_WEB,
                agent_name="agent_a",
            ),
            ResearchTask(
                task_id="t2", query="B", task_type=ResearchTaskType.SECONDARY_WEB,
                agent_name="agent_b", depends_on=["t1"],
            ),
        ]
        plan = ResearchPlan(original_query="test", tasks=tasks)

        # Budget already exhausted
        budget = ResearchBudget(max_api_calls=1, used_api_calls=1)

        agent_a = _make_agent("agent_a")
        agent_b = _make_agent("agent_b")

        strategy = ResearchDAGStrategy()
        context = AgentContext(
            user_message="test",
            metadata={
                "research_plan": plan.model_dump(),
                "research_budget": budget.model_dump(),
            },
        )
        await strategy.execute([agent_a, agent_b], context)

        # Neither agent should run since budget is exhausted from the start
        assert not agent_a.run.called
        assert not agent_b.run.called


class TestResearchDAGStrategyFailedTask:
    async def test_failed_task_skips_dependents(self):
        tasks = [
            ResearchTask(
                task_id="t1", query="A", task_type=ResearchTaskType.SECONDARY_WEB,
                agent_name="agent_a",
            ),
            ResearchTask(
                task_id="t2", query="B", task_type=ResearchTaskType.FACT_CHECK,
                agent_name="agent_b", depends_on=["t1"],
            ),
        ]
        plan = ResearchPlan(original_query="test", tasks=tasks)

        agent_a = AsyncMock(spec=Agent)
        agent_a.name = "agent_a"
        agent_a.run = AsyncMock(side_effect=Exception("Agent failed"))

        agent_b = _make_agent("agent_b")

        strategy = ResearchDAGStrategy()
        context = AgentContext(
            user_message="test",
            metadata={"research_plan": plan.model_dump()},
        )
        await strategy.execute([agent_a, agent_b], context)

        # agent_a was called but failed
        assert agent_a.run.called
        # agent_b should NOT have been called (depends on failed t1)
        assert not agent_b.run.called


class TestResearchDAGStrategyCallbacks:
    async def test_on_task_complete_callback(self):
        task = ResearchTask(
            task_id="t1", query="A", task_type=ResearchTaskType.SECONDARY_WEB,
            agent_name="agent_a",
        )
        plan = ResearchPlan(original_query="test", tasks=[task])

        callback = AsyncMock()
        agent = _make_agent("agent_a")

        strategy = ResearchDAGStrategy(on_task_complete=callback)
        context = AgentContext(
            user_message="test",
            metadata={"research_plan": plan.model_dump()},
        )
        await strategy.execute([agent], context)

        assert callback.called

    async def test_on_budget_update_callback(self):
        task = ResearchTask(
            task_id="t1", query="A", task_type=ResearchTaskType.SECONDARY_WEB,
            agent_name="agent_a",
        )
        plan = ResearchPlan(original_query="test", tasks=[task])

        budget_cb = AsyncMock()
        agent = _make_agent("agent_a")

        strategy = ResearchDAGStrategy(on_budget_update=budget_cb)
        context = AgentContext(
            user_message="test",
            metadata={
                "research_plan": plan.model_dump(),
                "research_budget": ResearchBudget().model_dump(),
            },
        )
        await strategy.execute([agent], context)

        assert budget_cb.called


class TestResearchDAGStrategyReflection:
    async def test_reflection_loop_adds_new_tasks(self):
        """After first wave, reflection agent adds new tasks, which are then executed."""
        tasks = [
            ResearchTask(
                task_id="t1", query="A", task_type=ResearchTaskType.SECONDARY_WEB,
                agent_name="web_researcher",
            ),
            ResearchTask(
                task_id="t_reflect", query="reflect", task_type=ResearchTaskType.REFLECTION,
                agent_name="reflection", depends_on=["t1"],
            ),
        ]
        plan = ResearchPlan(original_query="test", tasks=tasks, max_iterations=2)

        web_agent = _make_agent("web_researcher", metadata={"findings": [{"id": "f1"}]})

        # Reflection returns new tasks on first call, none on second
        new_task = ResearchTask(
            task_id="t2",
            query="Follow-up",
            task_type=ResearchTaskType.SECONDARY_WEB,
            agent_name="web_researcher",
        )
        reflection_agent = AsyncMock(spec=Agent)
        reflection_agent.name = "reflection"
        reflection_call_count = 0

        async def reflection_run(ctx):
            nonlocal reflection_call_count
            reflection_call_count += 1
            if reflection_call_count == 1:
                return AgentResult(
                    agent_name="reflection",
                    response="Found gaps",
                    metadata={"new_tasks": [new_task.model_dump()], "gaps": ["gap1"]},
                )
            return AgentResult(
                agent_name="reflection",
                response="Sufficient",
                metadata={"new_tasks": [], "gaps": []},
            )

        reflection_agent.run = AsyncMock(side_effect=reflection_run)

        strategy = ResearchDAGStrategy(max_iterations=2)
        context = AgentContext(
            user_message="test",
            metadata={"research_plan": plan.model_dump()},
        )
        await strategy.execute([web_agent, reflection_agent], context)

        # Web researcher should have been called at least twice (original + follow-up)
        assert web_agent.run.call_count >= 2


class TestResearchDAGStrategyMerge:
    async def test_merge_results_includes_misattributed_ids(self):
        tasks = [
            ResearchTask(
                task_id="t1", query="A", task_type=ResearchTaskType.SECONDARY_WEB,
                agent_name="web_researcher",
            ),
            ResearchTask(
                task_id="t2", query="check", task_type=ResearchTaskType.FACT_CHECK,
                agent_name="fact_checker", depends_on=["t1"],
            ),
        ]
        plan = ResearchPlan(original_query="test", tasks=tasks)

        web_agent = _make_agent("web_researcher", metadata={
            "findings": [{"finding_id": "f1"}, {"finding_id": "f2"}],
        })
        fact_agent = _make_agent("fact_checker", metadata={
            "checked_findings": [],
            "misattributed_ids": ["f1"],
        })

        strategy = ResearchDAGStrategy()
        context = AgentContext(
            user_message="test",
            metadata={"research_plan": plan.model_dump()},
        )
        result = await strategy.execute([web_agent, fact_agent], context)

        assert "f1" in result.metadata.get("misattributed_ids", [])
