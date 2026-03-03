from __future__ import annotations

from unittest.mock import AsyncMock

from src.applications.deep_search.models.research import (
    ResearchBudget,
    ResearchPlan,
    ResearchTask,
    ResearchTaskType,
)
from src.applications.deep_search.models.streaming import DeepSearchEventType
from src.applications.deep_search.streaming_pipeline import StreamableDeepSearchPipeline
from src.core.interfaces.agent import Agent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult
from src.core.orchestrator.strategies.research_dag import ResearchDAGStrategy


def _make_mock_agent(name: str, response: str = "ok", metadata: dict | None = None) -> Agent:
    agent = AsyncMock(spec=Agent)
    agent.name = name
    agent.description = f"Mock {name}"
    agent.run = AsyncMock(return_value=AgentResult(
        agent_name=name,
        response=response,
        metadata=metadata or {},
    ))
    return agent


class TestFullDeepSearchFlow:
    """Integration: planner -> research -> fact check -> reflection -> synthesis."""

    async def test_full_flow(self):
        # Planner produces a plan with 2 research tasks + fact check + reflection
        plan = ResearchPlan(
            original_query="What is quantum computing?",
            tasks=[
                ResearchTask(
                    task_id="t1", query="Quantum computing basics",
                    task_type=ResearchTaskType.SECONDARY_WEB,
                    agent_name="deep_web_researcher",
                ),
                ResearchTask(
                    task_id="t2", query="Quantum computing papers",
                    task_type=ResearchTaskType.SECONDARY_ACADEMIC,
                    agent_name="academic_researcher",
                ),
                ResearchTask(
                    task_id="t3", query="Verify quantum claims",
                    task_type=ResearchTaskType.FACT_CHECK,
                    agent_name="fact_checker",
                    depends_on=["t1", "t2"],
                ),
                ResearchTask(
                    task_id="t4", query="Reflect on completeness",
                    task_type=ResearchTaskType.REFLECTION,
                    agent_name="reflection",
                    depends_on=["t3"],
                ),
            ],
            max_iterations=1,
        )

        web_agent = _make_mock_agent(
            "deep_web_researcher",
            metadata={"findings": [{"finding_id": "f1", "content": "Quantum uses qubits"}]},
        )
        acad_agent = _make_mock_agent(
            "academic_researcher",
            metadata={"findings": [{"finding_id": "f2", "content": "Shor's algorithm"}]},
        )
        fact_agent = _make_mock_agent(
            "fact_checker",
            metadata={"checked_findings": [{"finding_id": "f1", "adjusted_confidence": 0.9}]},
        )
        reflect_agent = _make_mock_agent(
            "reflection",
            metadata={"gaps": [], "new_tasks": [], "overall_confidence": 0.85},
        )

        strategy = ResearchDAGStrategy(max_iterations=1)
        context = AgentContext(
            user_message="What is quantum computing?",
            metadata={"research_plan": plan.model_dump()},
        )
        result = await strategy.execute(
            [web_agent, acad_agent, fact_agent, reflect_agent],
            context,
        )

        # All agents should have been called
        assert web_agent.run.called
        assert acad_agent.run.called
        assert fact_agent.run.called
        assert reflect_agent.run.called
        assert result.agent_name == "research_dag"


class TestBudgetExhaustion:
    async def test_stops_research_gracefully(self):
        plan = ResearchPlan(
            original_query="test",
            tasks=[
                ResearchTask(
                    task_id="t1", query="A",
                    task_type=ResearchTaskType.SECONDARY_WEB,
                    agent_name="agent_a",
                ),
                ResearchTask(
                    task_id="t2", query="B",
                    task_type=ResearchTaskType.SECONDARY_WEB,
                    agent_name="agent_b",
                    depends_on=["t1"],
                ),
            ],
        )
        budget = ResearchBudget(max_api_calls=1, used_api_calls=0)

        agent_a = _make_mock_agent("agent_a")
        agent_b = _make_mock_agent("agent_b")

        strategy = ResearchDAGStrategy()
        context = AgentContext(
            user_message="test",
            metadata={
                "research_plan": plan.model_dump(),
                "research_budget": budget.model_dump(),
            },
        )
        await strategy.execute([agent_a, agent_b], context)

        # agent_a runs (uses 1 api call), agent_b should NOT run (budget exhausted)
        assert agent_a.run.called
        assert not agent_b.run.called


class TestReflectionLoop:
    async def test_generates_follow_up_tasks(self):
        tasks = [
            ResearchTask(
                task_id="t1", query="Initial research",
                task_type=ResearchTaskType.SECONDARY_WEB,
                agent_name="web_agent",
            ),
            ResearchTask(
                task_id="t_reflect", query="Reflect",
                task_type=ResearchTaskType.REFLECTION,
                agent_name="reflect_agent",
                depends_on=["t1"],
            ),
        ]
        plan = ResearchPlan(original_query="test", tasks=tasks, max_iterations=2)

        web_agent = _make_mock_agent("web_agent", metadata={"findings": [{"id": "f1"}]})

        reflect_call = 0

        async def reflect_side_effect(ctx):
            nonlocal reflect_call
            reflect_call += 1
            if reflect_call == 1:
                return AgentResult(
                    agent_name="reflect_agent",
                    response="Gaps found",
                    metadata={
                        "new_tasks": [{
                            "task_id": "t_new",
                            "query": "Follow-up",
                            "task_type": "secondary_web",
                            "depends_on": [],
                            "agent_name": "web_agent",
                        }],
                        "gaps": ["Missing info"],
                    },
                )
            return AgentResult(
                agent_name="reflect_agent",
                response="Sufficient",
                metadata={"new_tasks": [], "gaps": []},
            )

        reflect_agent = AsyncMock(spec=Agent)
        reflect_agent.name = "reflect_agent"
        reflect_agent.run = AsyncMock(side_effect=reflect_side_effect)

        strategy = ResearchDAGStrategy(max_iterations=2)
        context = AgentContext(
            user_message="test",
            metadata={"research_plan": plan.model_dump()},
        )
        await strategy.execute([web_agent, reflect_agent], context)

        # Web agent called at least 2x (original + follow-up)
        assert web_agent.run.call_count >= 2


class TestSSEEventSequence:
    async def test_correct_event_sequence(self):
        planner = AsyncMock()
        planner.name = "research_planner"
        planner.run = AsyncMock(return_value=AgentResult(
            agent_name="research_planner",
            response="Plan",
            metadata={
                "research_plan": {
                    "original_query": "test",
                    "tasks": [
                        {
                            "task_id": "t1",
                            "query": "test",
                            "task_type": "secondary_web",
                            "depends_on": [],
                            "agent_name": "web_agent",
                        },
                    ],
                    "max_iterations": 1,
                },
            },
        ))

        web_agent = _make_mock_agent(
            "web_agent",
            metadata={"findings": [{"finding_id": "f1", "content": "test", "source_url": "http://x.com"}]},
        )

        strategy = ResearchDAGStrategy()

        synthesizer = AsyncMock()
        synthesizer.name = "deep_synthesizer"

        async def mock_stream(ctx):
            yield "Report "
            yield "content."

        synthesizer.stream_run = mock_stream

        pipeline = StreamableDeepSearchPipeline(
            planner=planner,
            synthesizer=synthesizer,
            strategy=strategy,
            agents=[web_agent],
        )

        context = AgentContext(user_message="test")
        events = []
        async for event in pipeline.stream_run(context):
            events.append(event["event"])

        # Verify event ordering
        assert events[0] == DeepSearchEventType.PLANNING
        assert DeepSearchEventType.RESEARCHING in events
        assert DeepSearchEventType.SYNTHESIZING in events
        assert DeepSearchEventType.CHUNK in events
        assert events[-1] == DeepSearchEventType.DONE
