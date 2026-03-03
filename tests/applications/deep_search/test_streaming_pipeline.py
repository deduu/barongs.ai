from __future__ import annotations

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

        # Planner should receive entity_grounding in metadata
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
