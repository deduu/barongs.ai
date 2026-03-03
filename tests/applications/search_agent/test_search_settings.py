from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.applications.search_agent.agents.synthesizer import SynthesizerAgent
from src.applications.search_agent.agents.web_researcher import WebResearcherAgent
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext
from src.core.models.results import ToolResult


class TestSynthesizerTemperatureOverride:
    """Verify that the synthesizer reads temperature from context.metadata."""

    async def test_uses_default_temperature(self) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(
            return_value=LLMResponse(content="ok", model="gpt-4o")
        )
        agent = SynthesizerAgent(llm_provider=llm, model="gpt-4o")

        ctx = AgentContext(user_message="test", metadata={"sources": []})
        await agent.run(ctx)

        request = llm.generate.call_args[0][0]
        assert request.temperature == pytest.approx(0.3)

    async def test_temperature_override_from_metadata(self) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(
            return_value=LLMResponse(content="ok", model="gpt-4o")
        )
        agent = SynthesizerAgent(llm_provider=llm, model="gpt-4o")

        ctx = AgentContext(
            user_message="test",
            metadata={"sources": [], "temperature": 0.8},
        )
        await agent.run(ctx)

        request = llm.generate.call_args[0][0]
        assert request.temperature == pytest.approx(0.8)

    async def test_stream_run_uses_temperature_override(self) -> None:
        llm = AsyncMock()
        captured_request = None

        async def mock_stream(req: object) -> object:
            nonlocal captured_request
            captured_request = req
            for t in ["a"]:
                yield t

        llm.stream = mock_stream
        agent = SynthesizerAgent(llm_provider=llm, model="gpt-4o")

        ctx = AgentContext(
            user_message="test",
            metadata={"sources": [], "temperature": 0.1},
        )
        async for _ in agent.stream_run(ctx):
            pass

        assert captured_request is not None
        assert captured_request.temperature == pytest.approx(0.1)


class TestWebResearcherMaxSourcesOverride:
    """Verify that the web researcher reads max_sources from context.metadata."""

    def _make_agent(
        self,
        search_results: list[dict[str, str]] | None = None,
        max_sources: int = 8,
    ) -> WebResearcherAgent:
        if search_results is None:
            search_results = [
                {"title": f"R{i}", "url": f"https://example.com/{i}", "snippet": f"S{i}"}
                for i in range(10)
            ]

        mock_search = AsyncMock()
        mock_search.name = "search"
        mock_search.execute = AsyncMock(
            return_value=ToolResult(tool_name="search", output=search_results)
        )

        mock_fetcher = AsyncMock()
        mock_fetcher.name = "fetcher"
        mock_fetcher.execute = AsyncMock(
            return_value=ToolResult(tool_name="fetcher", output="content")
        )

        mock_validator = AsyncMock()
        mock_validator.name = "validator"
        mock_validator.execute = AsyncMock(
            return_value=ToolResult(
                tool_name="validator",
                output=[r["url"] for r in search_results],
            )
        )

        return WebResearcherAgent(
            search_tool=mock_search,
            content_fetcher=mock_fetcher,
            url_validator=mock_validator,
            max_sources=max_sources,
        )

    async def test_uses_default_max_sources(self) -> None:
        agent = self._make_agent(max_sources=8)
        ctx = AgentContext(user_message="test")
        result = await agent.run(ctx)

        sources = result.metadata["sources"]
        assert len(sources) == 8

    async def test_max_sources_override_from_metadata(self) -> None:
        agent = self._make_agent(max_sources=8)
        ctx = AgentContext(
            user_message="test",
            metadata={"max_sources": 3},
        )
        result = await agent.run(ctx)

        sources = result.metadata["sources"]
        assert len(sources) == 3

    async def test_max_sources_override_larger_than_results(self) -> None:
        """When override exceeds available results, all results are returned."""
        results = [
            {"title": "R1", "url": "https://example.com/1", "snippet": "S1"},
            {"title": "R2", "url": "https://example.com/2", "snippet": "S2"},
        ]
        agent = self._make_agent(search_results=results, max_sources=3)
        ctx = AgentContext(
            user_message="test",
            metadata={"max_sources": 15},
        )
        result = await agent.run(ctx)

        sources = result.metadata["sources"]
        assert len(sources) == 2


class TestSearchRequestValidation:
    """Verify SearchRequest model accepts and validates new fields."""

    def test_accepts_temperature(self) -> None:
        from src.applications.search_agent.routes import SearchRequest

        req = SearchRequest(query="test", temperature=0.5)
        assert req.temperature == 0.5

    def test_accepts_max_sources(self) -> None:
        from src.applications.search_agent.routes import SearchRequest

        req = SearchRequest(query="test", max_sources=10)
        assert req.max_sources == 10

    def test_accepts_search_max_results(self) -> None:
        from src.applications.search_agent.routes import SearchRequest

        req = SearchRequest(query="test", search_max_results=25)
        assert req.search_max_results == 25

    def test_defaults_are_none(self) -> None:
        from src.applications.search_agent.routes import SearchRequest

        req = SearchRequest(query="test")
        assert req.temperature is None
        assert req.max_sources is None
        assert req.search_max_results is None

    def test_temperature_validation_rejects_out_of_range(self) -> None:
        from pydantic import ValidationError

        from src.applications.search_agent.routes import SearchRequest

        with pytest.raises(ValidationError):
            SearchRequest(query="test", temperature=1.5)

    def test_max_sources_validation_rejects_out_of_range(self) -> None:
        from pydantic import ValidationError

        from src.applications.search_agent.routes import SearchRequest

        with pytest.raises(ValidationError):
            SearchRequest(query="test", max_sources=1)
