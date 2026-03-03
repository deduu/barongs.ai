from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from src.applications.deep_search.models.outline import (
    OutlineConfirmation,
    OutlineSection,
    ResearchOutline,
    ResearchTask,
)
from src.applications.deep_search.session_store import PipelineSession, SessionStore
from src.core.models.context import AgentContext

# --- Pydantic model tests ---


class TestOutlineModels:
    def test_outline_section_creation(self) -> None:
        section = OutlineSection(heading="Introduction", description="Background and context")
        assert section.heading == "Introduction"
        assert section.description == "Background and context"

    def test_research_task_creation(self) -> None:
        task = ResearchTask(
            task_id="t1",
            query="What is X?",
            task_type="secondary_web",
            agent_name="deep_web_researcher",
        )
        assert task.task_id == "t1"
        assert task.depends_on == []

    def test_research_outline_creation(self) -> None:
        outline = ResearchOutline(
            session_id="sess-1",
            query="test query",
            research_mode="academic",
            sections=[OutlineSection(heading="Intro", description="Background")],
            research_tasks=[
                ResearchTask(
                    task_id="t1",
                    query="sub-query",
                    task_type="secondary_web",
                    agent_name="deep_web_researcher",
                )
            ],
        )
        assert outline.session_id == "sess-1"
        assert len(outline.sections) == 1
        assert len(outline.research_tasks) == 1

    def test_outline_confirmation_approve(self) -> None:
        confirm = OutlineConfirmation(session_id="sess-1", approved=True)
        assert confirm.approved is True
        assert confirm.sections is None
        assert confirm.research_tasks is None

    def test_outline_confirmation_with_edits(self) -> None:
        confirm = OutlineConfirmation(
            session_id="sess-1",
            approved=True,
            sections=[OutlineSection(heading="Custom Section", description="Custom desc")],
            research_tasks=[
                ResearchTask(
                    task_id="t1",
                    query="modified query",
                    task_type="secondary_academic",
                    agent_name="academic_researcher",
                )
            ],
        )
        assert len(confirm.sections) == 1
        assert confirm.research_tasks[0].query == "modified query"


# --- SessionStore tests ---


class TestSessionStore:
    def test_create_session(self) -> None:
        store = SessionStore()
        session = store.create("sess-1")
        assert isinstance(session, PipelineSession)
        assert session.session_id == "sess-1"

    def test_get_session(self) -> None:
        store = SessionStore()
        store.create("sess-1")
        session = store.get("sess-1")
        assert session is not None
        assert session.session_id == "sess-1"

    def test_get_missing_session(self) -> None:
        store = SessionStore()
        assert store.get("nonexistent") is None

    def test_remove_session(self) -> None:
        store = SessionStore()
        store.create("sess-1")
        store.remove("sess-1")
        assert store.get("sess-1") is None

    def test_remove_missing_session_no_error(self) -> None:
        store = SessionStore()
        store.remove("nonexistent")  # Should not raise


# --- PipelineSession tests ---


class TestPipelineSession:
    async def test_confirm_unblocks_wait(self) -> None:
        session = PipelineSession("sess-1")

        async def _confirm_after_delay() -> None:
            await asyncio.sleep(0.05)
            session.confirm({"approved": True})

        asyncio.create_task(_confirm_after_delay())
        result = await session.wait_for_confirmation(timeout=5.0)

        assert result is not None
        assert result["approved"] is True

    async def test_timeout_returns_none(self) -> None:
        session = PipelineSession("sess-1")
        result = await session.wait_for_confirmation(timeout=0.1)
        assert result is None

    async def test_confirm_with_edited_data(self) -> None:
        session = PipelineSession("sess-1")
        edit_data = {
            "approved": True,
            "sections": [{"heading": "Custom"}],
            "research_tasks": [{"task_id": "t1", "query": "modified"}],
        }

        async def _confirm() -> None:
            await asyncio.sleep(0.05)
            session.confirm(edit_data)

        asyncio.create_task(_confirm())
        result = await session.wait_for_confirmation(timeout=5.0)

        assert result is not None
        assert result["sections"][0]["heading"] == "Custom"
        assert result["research_tasks"][0]["query"] == "modified"


# --- Streaming pipeline interactive tests ---


class TestStreamingPipelineInteractive:
    async def test_non_interactive_does_not_pause(self) -> None:
        """With interactive_outline=False, pipeline should not emit OUTLINE_READY."""
        from src.applications.deep_search.models.streaming import DeepSearchEventType
        from src.applications.deep_search.streaming_pipeline import StreamableDeepSearchPipeline

        mock_planner = MagicMock()
        mock_planner.run = AsyncMock(
            return_value=MagicMock(
                metadata={"research_plan": {"tasks": [], "original_query": "test"}},
            )
        )
        mock_synthesizer = MagicMock()

        async def _stream(*_a: Any, **_kw: Any) -> Any:
            yield "token"

        mock_synthesizer.stream_run = _stream

        mock_strategy = MagicMock()
        mock_strategy.execute = AsyncMock(
            return_value=MagicMock(metadata={"findings": [], "misattributed_ids": []})
        )

        store = SessionStore()
        pipeline = StreamableDeepSearchPipeline(
            planner=mock_planner,
            synthesizer=mock_synthesizer,
            strategy=mock_strategy,
            agents=[],
            session_store=store,
        )

        context = AgentContext(
            user_message="test",
            metadata={"interactive_outline": False},
        )

        events = []
        async for event in pipeline.stream_run(context):
            events.append(event)

        event_types = [e["event"] for e in events]
        assert DeepSearchEventType.OUTLINE_READY not in event_types

    async def test_interactive_emits_outline_ready(self) -> None:
        """With interactive_outline=True, pipeline should emit OUTLINE_READY and pause."""
        from src.applications.deep_search.models.streaming import DeepSearchEventType
        from src.applications.deep_search.streaming_pipeline import StreamableDeepSearchPipeline

        mock_planner = MagicMock()
        mock_planner.run = AsyncMock(
            return_value=MagicMock(
                metadata={
                    "research_plan": {
                        "tasks": [
                            {
                                "task_id": "t1",
                                "query": "sub-query",
                                "task_type": "secondary_web",
                                "agent_name": "deep_web_researcher",
                                "depends_on": [],
                            }
                        ],
                        "original_query": "test",
                    },
                },
            )
        )
        mock_synthesizer = MagicMock()

        async def _stream(*_a: Any, **_kw: Any) -> Any:
            yield "token"

        mock_synthesizer.stream_run = _stream

        mock_strategy = MagicMock()
        mock_strategy.execute = AsyncMock(
            return_value=MagicMock(metadata={"findings": [], "misattributed_ids": []})
        )

        store = SessionStore()
        pipeline = StreamableDeepSearchPipeline(
            planner=mock_planner,
            synthesizer=mock_synthesizer,
            strategy=mock_strategy,
            agents=[],
            session_store=store,
        )

        context = AgentContext(
            user_message="test",
            session_id="test-session",
            metadata={"interactive_outline": True, "research_mode": "general"},
        )

        events: list[dict[str, Any]] = []

        async def _collect_and_confirm() -> None:
            """Collect events, and when AWAITING_CONFIRMATION appears, confirm."""
            async for event in pipeline.stream_run(context):
                events.append(event)
                if event["event"] == DeepSearchEventType.AWAITING_CONFIRMATION:
                    # Simulate user confirming after a short delay
                    session = store.get("test-session")
                    assert session is not None
                    session.confirm({"approved": True})

        await _collect_and_confirm()

        event_types = [e["event"] for e in events]
        assert DeepSearchEventType.OUTLINE_READY in event_types
        assert DeepSearchEventType.AWAITING_CONFIRMATION in event_types
        assert DeepSearchEventType.OUTLINE_CONFIRMED in event_types
        assert DeepSearchEventType.DONE in event_types

    async def test_interactive_timeout_emits_error(self) -> None:
        """If user doesn't confirm within timeout, pipeline should emit ERROR."""
        from src.applications.deep_search.models.streaming import DeepSearchEventType
        from src.applications.deep_search.streaming_pipeline import StreamableDeepSearchPipeline

        mock_planner = MagicMock()
        mock_planner.run = AsyncMock(
            return_value=MagicMock(
                metadata={
                    "research_plan": {
                        "tasks": [
                            {
                                "task_id": "t1",
                                "query": "sub-query",
                                "task_type": "secondary_web",
                                "agent_name": "deep_web_researcher",
                                "depends_on": [],
                            }
                        ],
                        "original_query": "test",
                    },
                },
            )
        )
        mock_synthesizer = MagicMock()
        mock_strategy = MagicMock()

        store = SessionStore()
        pipeline = StreamableDeepSearchPipeline(
            planner=mock_planner,
            synthesizer=mock_synthesizer,
            strategy=mock_strategy,
            agents=[],
            session_store=store,
            outline_timeout=0.1,  # Very short timeout for test
        )

        context = AgentContext(
            user_message="test",
            session_id="test-session",
            metadata={"interactive_outline": True},
        )

        events: list[dict[str, Any]] = []
        async for event in pipeline.stream_run(context):
            events.append(event)

        event_types = [e["event"] for e in events]
        assert DeepSearchEventType.OUTLINE_READY in event_types
        assert DeepSearchEventType.ERROR in event_types
