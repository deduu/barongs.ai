from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

from src.applications.deep_search.models.streaming import DeepSearchEventType
from src.applications.deep_search.streaming_pipeline import StreamableDeepSearchPipeline
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult, ToolResult


class TestStreamableDeepSearchPipeline:
    async def test_stream_emits_planning_event(self):
        planner = AsyncMock()
        planner.name = "research_planner"
        planner.run = AsyncMock(return_value=AgentResult(
            agent_name="research_planner",
            response="Plan created",
            metadata={
                "research_plan": {
                    "original_query": "test",
                    "tasks": [],
                    "max_iterations": 1,
                },
            },
        ))

        synthesizer = AsyncMock()
        synthesizer.name = "deep_synthesizer"

        async def mock_stream(ctx):
            yield "Final "
            yield "report."

        synthesizer.stream_run = mock_stream

        from src.core.orchestrator.strategies.research_dag import ResearchDAGStrategy

        strategy = ResearchDAGStrategy()

        pipeline = StreamableDeepSearchPipeline(
            planner=planner,
            synthesizer=synthesizer,
            strategy=strategy,
            agents=[],
        )

        context = AgentContext(user_message="test query")
        events = []
        async for event in pipeline.stream_run(context):
            events.append(event)

        event_types = [e["event"] for e in events]
        assert DeepSearchEventType.PLANNING in event_types
        assert DeepSearchEventType.SYNTHESIZING in event_types
        assert DeepSearchEventType.DONE in event_types

    async def test_stream_emits_chunk_events(self):
        planner = AsyncMock()
        planner.name = "research_planner"
        planner.run = AsyncMock(return_value=AgentResult(
            agent_name="research_planner",
            response="Plan created",
            metadata={
                "research_plan": {
                    "original_query": "test",
                    "tasks": [],
                    "max_iterations": 1,
                },
            },
        ))

        synthesizer = AsyncMock()
        synthesizer.name = "deep_synthesizer"

        async def mock_stream(ctx):
            for word in ["Hello", " ", "World"]:
                yield word

        synthesizer.stream_run = mock_stream

        strategy = AsyncMock()
        strategy.execute = AsyncMock(return_value=AgentResult(
            agent_name="research_dag",
            response="Research done",
            metadata={"findings": [{"id": "f1", "content": "test finding"}]},
        ))

        academic_agent = AsyncMock()
        academic_agent.name = "academic_researcher"

        pipeline = StreamableDeepSearchPipeline(
            planner=planner,
            synthesizer=synthesizer,
            strategy=strategy,
            agents=[academic_agent],
        )

        context = AgentContext(user_message="test")
        events = []
        async for event in pipeline.stream_run(context):
            events.append(event)

        chunk_events = [e for e in events if e["event"] == DeepSearchEventType.CHUNK]
        assert len(chunk_events) == 3
        chunks = "".join(e["data"]["token"] for e in chunk_events)
        assert chunks == "Hello World"

    async def test_stream_emits_error_on_failure(self):
        planner = AsyncMock()
        planner.name = "research_planner"
        planner.run = AsyncMock(side_effect=Exception("Planner failed"))

        pipeline = StreamableDeepSearchPipeline(
            planner=planner,
            synthesizer=AsyncMock(),
            strategy=AsyncMock(),
            agents=[],
        )

        context = AgentContext(user_message="test")
        events = []
        async for event in pipeline.stream_run(context):
            events.append(event)

        event_types = [e["event"] for e in events]
        assert DeepSearchEventType.ERROR in event_types

    async def test_phase_0_fetches_user_urls_and_builds_grounding(self):
        """When query contains URLs, Phase 0 fetches them and builds entity grounding."""
        content_fetcher = AsyncMock()
        content_fetcher.name = "content_fetcher"
        content_fetcher.execute = AsyncMock(return_value=ToolResult(
            tool_name="content_fetcher",
            output="Auditi is a CLI tool for auditing GitHub repos.",
        ))

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content=json.dumps({
                "name": "Auditi",
                "description": "A CLI tool for GitHub auditing",
                "key_attributes": ["GitHub", "CLI"],
            }),
            model="test",
        ))

        planner = AsyncMock()
        planner.name = "research_planner"
        planner.run = AsyncMock(return_value=AgentResult(
            agent_name="research_planner",
            response="Plan created",
            metadata={"research_plan": {"original_query": "test", "tasks": [], "max_iterations": 1}},
        ))

        synthesizer = AsyncMock()

        async def mock_stream(ctx):
            yield "Report."

        synthesizer.stream_run = mock_stream

        pipeline = StreamableDeepSearchPipeline(
            planner=planner,
            synthesizer=synthesizer,
            strategy=AsyncMock(),
            agents=[],
            content_fetcher=content_fetcher,
            llm_provider=llm,
        )

        context = AgentContext(
            user_message="What is auditi? https://github.com/deduu/auditi",
        )
        events = []
        async for event in pipeline.stream_run(context):
            events.append(event)

        # Should have STATUS events for URL fetching and entity grounding
        status_events = [e for e in events if e["event"] == DeepSearchEventType.STATUS]
        assert any("fetching" in e["data"].get("status", "") for e in status_events)
        assert any("entity grounded" in e["data"].get("status", "") for e in status_events)

        # Planner orchestrator delegates to planner.run — check the context it received
        planner_call_ctx = planner.run.call_args[0][0]
        assert "entity_grounding" in planner_call_ctx.metadata
        assert planner_call_ctx.metadata["entity_grounding"]["name"] == "Auditi"

    async def test_entity_grounding_built_without_urls(self):
        """When no URLs in query, entity grounding is still built from query text."""
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content=json.dumps({
                "name": "Python GIL",
                "description": "Python Global Interpreter Lock",
                "key_attributes": [],
            }),
            model="test",
        ))

        planner = AsyncMock()
        planner.name = "research_planner"
        planner.run = AsyncMock(return_value=AgentResult(
            agent_name="research_planner",
            response="Plan created",
            metadata={"research_plan": {"original_query": "test", "tasks": [], "max_iterations": 1}},
        ))

        synthesizer = AsyncMock()

        async def mock_stream(ctx):
            yield "Report."

        synthesizer.stream_run = mock_stream

        pipeline = StreamableDeepSearchPipeline(
            planner=planner,
            synthesizer=synthesizer,
            strategy=AsyncMock(),
            agents=[],
            llm_provider=llm,
        )

        context = AgentContext(user_message="How does Python GIL work?")
        events = []
        async for event in pipeline.stream_run(context):
            events.append(event)

        planner_call_ctx = planner.run.call_args[0][0]
        assert "entity_grounding" in planner_call_ctx.metadata
        assert planner_call_ctx.metadata["entity_grounding"]["name"] == "Python GIL"

    async def test_misattributed_findings_filtered_before_synthesis(self):
        """Findings with misattributed_ids from DAG are excluded before synthesis."""
        planner = AsyncMock()
        planner.name = "research_planner"
        planner.run = AsyncMock(return_value=AgentResult(
            agent_name="research_planner",
            response="Plan",
            metadata={"research_plan": {"original_query": "test", "tasks": [{"task_id": "t1", "query": "test", "task_type": "secondary_web", "depends_on": [], "agent_name": "deep_web_researcher"}], "max_iterations": 1}},
        ))

        strategy = AsyncMock()
        strategy.execute = AsyncMock(return_value=AgentResult(
            agent_name="research_dag",
            response="Done",
            metadata={
                "findings": [
                    {"finding_id": "f1", "content": "wrong entity"},
                    {"finding_id": "f2", "content": "correct entity"},
                ],
                "misattributed_ids": ["f1"],
                "attempted_sources": [{"url": "https://example.com/paper", "status": "finding_extracted"}],
            },
        ))

        synthesizer = AsyncMock()
        synth_ctx_holder: list[AgentContext] = []

        async def mock_stream(ctx):
            synth_ctx_holder.append(ctx)
            yield "Report."

        synthesizer.stream_run = mock_stream

        pipeline = StreamableDeepSearchPipeline(
            planner=planner,
            synthesizer=synthesizer,
            strategy=strategy,
            agents=[],
        )

        context = AgentContext(user_message="test")
        events = []
        async for event in pipeline.stream_run(context):
            events.append(event)

        # Synthesizer should only receive f2
        synth_findings = synth_ctx_holder[0].metadata["findings"]
        assert len(synth_findings) == 1
        assert synth_findings[0]["finding_id"] == "f2"
        assert synth_ctx_holder[0].metadata["attempted_sources"][0]["url"] == "https://example.com/paper"

    async def test_planner_uses_orchestrator(self):
        """Verify the planner call goes through an Orchestrator (has timeout)."""
        planner = AsyncMock()
        planner.name = "research_planner"
        planner.run = AsyncMock(return_value=AgentResult(
            agent_name="research_planner",
            response="Plan created",
            metadata={
                "research_plan": {
                    "original_query": "test",
                    "tasks": [],
                    "max_iterations": 1,
                },
            },
        ))

        synthesizer = AsyncMock()

        async def mock_stream(ctx):
            yield "Report."

        synthesizer.stream_run = mock_stream

        pipeline = StreamableDeepSearchPipeline(
            planner=planner,
            synthesizer=synthesizer,
            strategy=AsyncMock(),
            agents=[],
            timeout_seconds=60.0,
        )

        # Verify internal orchestrator exists and has correct timeout
        assert hasattr(pipeline, "_planner_orchestrator")
        assert pipeline._planner_orchestrator._timeout_seconds == 60.0

        context = AgentContext(user_message="test")
        events = []
        async for event in pipeline.stream_run(context):
            events.append(event)

        # Planner should still be called (via orchestrator)
        planner.run.assert_awaited_once()

    async def test_dag_uses_orchestrator(self):
        """Verify DAG research goes through an Orchestrator."""
        planner = AsyncMock()
        planner.name = "research_planner"
        planner.run = AsyncMock(return_value=AgentResult(
            agent_name="research_planner",
            response="Plan",
            metadata={"research_plan": {
                "original_query": "test",
                "tasks": [{"task_id": "t1", "query": "q", "task_type": "secondary_web", "depends_on": [], "agent_name": "deep_web_researcher"}],
                "max_iterations": 1,
            }},
        ))

        strategy = AsyncMock()
        strategy.execute = AsyncMock(return_value=AgentResult(
            agent_name="research_dag",
            response="Done",
            metadata={"findings": []},
        ))

        synthesizer = AsyncMock()

        async def mock_stream(ctx):
            yield "Report."

        synthesizer.stream_run = mock_stream

        pipeline = StreamableDeepSearchPipeline(
            planner=planner,
            synthesizer=synthesizer,
            strategy=strategy,
            agents=[],
            timeout_seconds=120.0,
        )

        assert hasattr(pipeline, "_dag_orchestrator")
        assert pipeline._dag_orchestrator._timeout_seconds == 120.0

        context = AgentContext(user_message="test")
        events = []
        async for event in pipeline.stream_run(context):
            events.append(event)

        # DAG strategy should be called (via orchestrator.run -> strategy.execute)
        strategy.execute.assert_awaited_once()

    async def test_dag_receives_research_budget_from_request(self):
        planner = AsyncMock()
        planner.name = "research_planner"
        planner.run = AsyncMock(return_value=AgentResult(
            agent_name="research_planner",
            response="Plan",
            metadata={"research_plan": {
                "original_query": "test",
                "tasks": [{"task_id": "t1", "query": "q", "task_type": "secondary_web", "depends_on": [], "agent_name": "deep_web_researcher"}],
                "max_iterations": 1,
            }},
        ))

        strategy = AsyncMock()
        strategy.execute = AsyncMock(return_value=AgentResult(
            agent_name="research_dag",
            response="Done",
            metadata={"findings": []},
        ))

        synthesizer = AsyncMock()

        async def mock_stream(ctx):
            yield "Report."

        synthesizer.stream_run = mock_stream

        pipeline = StreamableDeepSearchPipeline(
            planner=planner,
            synthesizer=synthesizer,
            strategy=strategy,
            agents=[],
            research_max_llm_tokens=12345,
            research_max_api_calls=77,
            research_max_time_seconds=999,
        )

        context = AgentContext(
            user_message="test",
            metadata={"max_time_seconds": 180, "max_iterations": 4},
        )
        async for _ in pipeline.stream_run(context):
            pass

        strategy_ctx = strategy.execute.await_args.args[1]
        budget = strategy_ctx.metadata["research_budget"]
        assert budget["max_time_seconds"] == 180.0
        assert budget["max_llm_tokens"] == 12345
        assert budget["max_api_calls"] == 77
        assert strategy_ctx.metadata["research_plan"]["max_iterations"] == 4

    async def test_pipeline_adds_academic_task_when_enabled_and_missing(self):
        planner = AsyncMock()
        planner.name = "research_planner"
        planner.run = AsyncMock(return_value=AgentResult(
            agent_name="research_planner",
            response="Plan",
            metadata={"research_plan": {
                "original_query": "test",
                "tasks": [{"task_id": "t1", "query": "q", "task_type": "secondary_web", "depends_on": [], "agent_name": "deep_web_researcher"}],
                "max_iterations": 1,
            }},
        ))

        strategy = AsyncMock()
        strategy.execute = AsyncMock(return_value=AgentResult(
            agent_name="research_dag",
            response="Done",
            metadata={"findings": []},
        ))

        synthesizer = AsyncMock()

        async def mock_stream(ctx):
            yield "Report."

        synthesizer.stream_run = mock_stream

        academic_agent = AsyncMock()
        academic_agent.name = "academic_researcher"

        pipeline = StreamableDeepSearchPipeline(
            planner=planner,
            synthesizer=synthesizer,
            strategy=strategy,
            agents=[academic_agent],
        )

        context = AgentContext(
            user_message="OpenClaw safety",
            metadata={"enable_academic_search": True},
        )
        async for _ in pipeline.stream_run(context):
            pass

        strategy_ctx = strategy.execute.await_args.args[1]
        tasks = strategy_ctx.metadata["research_plan"]["tasks"]
        assert any(task["agent_name"] == "academic_researcher" for task in tasks)
        assert any(task["task_type"] == "secondary_academic" for task in tasks)

    async def test_pipeline_emits_task_progress_updates(self):
        planner = AsyncMock()
        planner.name = "research_planner"
        planner.run = AsyncMock(return_value=AgentResult(
            agent_name="research_planner",
            response="Plan",
            metadata={"research_plan": {
                "original_query": "test",
                "tasks": [{"task_id": "t1", "query": "q", "task_type": "secondary_web", "depends_on": [], "agent_name": "deep_web_researcher"}],
                "max_iterations": 1,
            }},
        ))

        from src.core.orchestrator.strategies.research_dag import ResearchDAGStrategy

        strategy = ResearchDAGStrategy()
        researcher = AsyncMock()
        researcher.name = "deep_web_researcher"
        researcher.run = AsyncMock(return_value=AgentResult(
            agent_name="deep_web_researcher",
            response="Done",
            metadata={"findings": [{"finding_id": "f1"}]},
        ))

        synthesizer = AsyncMock()

        async def mock_stream(ctx):
            yield "Report."

        synthesizer.stream_run = mock_stream

        pipeline = StreamableDeepSearchPipeline(
            planner=planner,
            synthesizer=synthesizer,
            strategy=strategy,
            agents=[researcher],
        )

        context = AgentContext(user_message="test")
        events = []
        async for event in pipeline.stream_run(context):
            events.append(event)

        researching_events = [e for e in events if e["event"] == DeepSearchEventType.RESEARCHING]
        assert any("running" in e["data"].get("status", "") for e in researching_events)
        assert any(e["data"].get("task_id") == "t1" for e in researching_events)

    async def test_pipeline_emits_clear_timeout_error(self):
        planner = AsyncMock()
        planner.name = "research_planner"
        planner.run = AsyncMock(return_value=AgentResult(
            agent_name="research_planner",
            response="Plan",
            metadata={"research_plan": {"original_query": "test", "tasks": [], "max_iterations": 1}},
        ))

        synthesizer = AsyncMock()

        async def broken_stream(_ctx):
            raise asyncio.TimeoutError
            yield "never"

        synthesizer.stream_run = broken_stream

        pipeline = StreamableDeepSearchPipeline(
            planner=planner,
            synthesizer=synthesizer,
            strategy=AsyncMock(),
            agents=[],
        )

        context = AgentContext(user_message="test")
        events = []
        async for event in pipeline.stream_run(context):
            events.append(event)

        assert events[-1]["event"] == DeepSearchEventType.ERROR
        assert "timed out before completion" in events[-1]["data"]["error"]
