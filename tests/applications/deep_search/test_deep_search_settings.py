from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.applications.deep_search.agents.deep_synthesizer import DeepSynthesizerAgent
from src.applications.deep_search.agents.deep_web_researcher import DeepWebResearcherAgent
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext
from src.core.models.results import ToolResult


class TestDeepSynthesizerTemperatureOverride:
    """Verify that the deep synthesizer reads temperature from context.metadata."""

    async def test_uses_default_temperature(self) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(
            return_value=LLMResponse(content="Report.", model="test", usage={"total_tokens": 50})
        )
        agent = DeepSynthesizerAgent(llm_provider=llm)

        ctx = AgentContext(user_message="test", metadata={"findings": []})
        await agent.run(ctx)

        request = llm.generate.call_args[0][0]
        assert request.temperature == pytest.approx(0.3)

    async def test_temperature_override_from_metadata(self) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(
            return_value=LLMResponse(content="Report.", model="test", usage={"total_tokens": 50})
        )
        agent = DeepSynthesizerAgent(llm_provider=llm)

        ctx = AgentContext(
            user_message="test",
            metadata={"findings": [], "temperature": 0.7},
        )
        await agent.run(ctx)

        request = llm.generate.call_args[0][0]
        assert request.temperature == pytest.approx(0.7)

    async def test_stream_run_uses_temperature_override(self) -> None:
        llm = AsyncMock()
        captured_request = None

        async def mock_stream(req: object) -> object:
            nonlocal captured_request
            captured_request = req
            for t in ["a"]:
                yield t

        llm.stream = mock_stream
        agent = DeepSynthesizerAgent(llm_provider=llm)

        ctx = AgentContext(
            user_message="test",
            metadata={"findings": [], "temperature": 0.9},
        )
        async for _ in agent.stream_run(ctx):
            pass

        assert captured_request is not None
        assert captured_request.temperature == pytest.approx(0.9)


class TestDeepWebResearcherSettingsOverride:
    """Verify that deep web researcher reads max_sources and extraction_detail from metadata."""

    def _make_tools(self) -> tuple[AsyncMock, AsyncMock, AsyncMock]:
        search_tool = AsyncMock()
        search_tool.name = "search"
        search_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="search",
            output=[
                {"title": f"Page {i}", "url": f"https://example.com/{i}", "snippet": f"s{i}"}
                for i in range(10)
            ],
        ))

        crawler_tool = AsyncMock()
        crawler_tool.name = "deep_crawler"
        crawler_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="deep_crawler",
            output={"pages": [{"content": "content", "depth": 0}], "links_followed": 0},
        ))

        scorer_tool = AsyncMock()
        scorer_tool.name = "source_scorer"
        scorer_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="source_scorer", output={"overall_score": 0.5},
        ))

        return search_tool, crawler_tool, scorer_tool

    async def test_max_sources_override(self) -> None:
        search_tool, crawler_tool, scorer_tool = self._make_tools()
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content="Finding.", model="test", usage={"total_tokens": 10},
        ))

        agent = DeepWebResearcherAgent(
            llm_provider=llm,
            search_tool=search_tool,
            deep_crawler_tool=crawler_tool,
            source_scorer_tool=scorer_tool,
            max_sources=5,
        )
        ctx = AgentContext(
            user_message="test",
            metadata={"max_sources": 2},
        )
        result = await agent.run(ctx)

        # Only 2 sources should be processed
        assert len(result.metadata["findings"]) <= 2
        # LLM should be called at most 2 times (once per source)
        assert llm.generate.call_count <= 2

    async def test_uses_default_max_sources(self) -> None:
        search_tool, crawler_tool, scorer_tool = self._make_tools()
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content="Finding.", model="test", usage={"total_tokens": 10},
        ))

        agent = DeepWebResearcherAgent(
            llm_provider=llm,
            search_tool=search_tool,
            deep_crawler_tool=crawler_tool,
            source_scorer_tool=scorer_tool,
            max_sources=5,
        )
        ctx = AgentContext(user_message="test")
        await agent.run(ctx)

        # Default 5 sources → LLM called 5 times
        assert llm.generate.call_count == 5

    async def test_extraction_detail_low_maps_to_400_tokens(self) -> None:
        search_tool, crawler_tool, scorer_tool = self._make_tools()
        # Limit to 1 source for simplicity
        search_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="search",
            output=[{"title": "P", "url": "https://example.com/1", "snippet": "s"}],
        ))

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content="Finding.", model="test", usage={"total_tokens": 10},
        ))

        agent = DeepWebResearcherAgent(
            llm_provider=llm,
            search_tool=search_tool,
            deep_crawler_tool=crawler_tool,
            source_scorer_tool=scorer_tool,
        )
        ctx = AgentContext(
            user_message="test",
            metadata={"extraction_detail": "low"},
        )
        await agent.run(ctx)

        request = llm.generate.call_args[0][0]
        assert request.max_tokens == 400

    async def test_extraction_detail_medium_maps_to_800_tokens(self) -> None:
        search_tool, crawler_tool, scorer_tool = self._make_tools()
        search_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="search",
            output=[{"title": "P", "url": "https://example.com/1", "snippet": "s"}],
        ))

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content="Finding.", model="test", usage={"total_tokens": 10},
        ))

        agent = DeepWebResearcherAgent(
            llm_provider=llm,
            search_tool=search_tool,
            deep_crawler_tool=crawler_tool,
            source_scorer_tool=scorer_tool,
        )
        ctx = AgentContext(user_message="test", metadata={"extraction_detail": "medium"})
        await agent.run(ctx)

        request = llm.generate.call_args[0][0]
        assert request.max_tokens == 800

    async def test_extraction_detail_high_maps_to_1200_tokens(self) -> None:
        search_tool, crawler_tool, scorer_tool = self._make_tools()
        search_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="search",
            output=[{"title": "P", "url": "https://example.com/1", "snippet": "s"}],
        ))

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content="Finding.", model="test", usage={"total_tokens": 10},
        ))

        agent = DeepWebResearcherAgent(
            llm_provider=llm,
            search_tool=search_tool,
            deep_crawler_tool=crawler_tool,
            source_scorer_tool=scorer_tool,
        )
        ctx = AgentContext(user_message="test", metadata={"extraction_detail": "high"})
        await agent.run(ctx)

        request = llm.generate.call_args[0][0]
        assert request.max_tokens == 1200

    async def test_default_extraction_detail_is_medium(self) -> None:
        search_tool, crawler_tool, scorer_tool = self._make_tools()
        search_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="search",
            output=[{"title": "P", "url": "https://example.com/1", "snippet": "s"}],
        ))

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content="Finding.", model="test", usage={"total_tokens": 10},
        ))

        agent = DeepWebResearcherAgent(
            llm_provider=llm,
            search_tool=search_tool,
            deep_crawler_tool=crawler_tool,
            source_scorer_tool=scorer_tool,
        )
        # No extraction_detail in metadata
        ctx = AgentContext(user_message="test")
        await agent.run(ctx)

        request = llm.generate.call_args[0][0]
        assert request.max_tokens == 800


class TestDeepSearchRequestValidation:
    """Verify DeepSearchRequest model accepts and validates new fields."""

    def test_accepts_temperature(self) -> None:
        from src.applications.deep_search.models.api import DeepSearchRequest

        req = DeepSearchRequest(query="test", temperature=0.5)
        assert req.temperature == 0.5

    def test_accepts_extraction_detail(self) -> None:
        from src.applications.deep_search.models.api import DeepSearchRequest

        for detail in ("low", "medium", "high"):
            req = DeepSearchRequest(query="test", extraction_detail=detail)
            assert req.extraction_detail == detail

    def test_accepts_crawl_depth(self) -> None:
        from src.applications.deep_search.models.api import DeepSearchRequest

        req = DeepSearchRequest(query="test", crawl_depth=3)
        assert req.crawl_depth == 3

    def test_accepts_max_sources(self) -> None:
        from src.applications.deep_search.models.api import DeepSearchRequest

        req = DeepSearchRequest(query="test", max_sources=7)
        assert req.max_sources == 7

    def test_defaults_are_none(self) -> None:
        from src.applications.deep_search.models.api import DeepSearchRequest

        req = DeepSearchRequest(query="test")
        assert req.temperature is None
        assert req.max_sources is None
        assert req.extraction_detail is None
        assert req.crawl_depth is None

    def test_invalid_extraction_detail_rejected(self) -> None:
        from pydantic import ValidationError

        from src.applications.deep_search.models.api import DeepSearchRequest

        with pytest.raises(ValidationError):
            DeepSearchRequest(query="test", extraction_detail="ultra")

    def test_crawl_depth_out_of_range_rejected(self) -> None:
        from pydantic import ValidationError

        from src.applications.deep_search.models.api import DeepSearchRequest

        with pytest.raises(ValidationError):
            DeepSearchRequest(query="test", crawl_depth=5)
