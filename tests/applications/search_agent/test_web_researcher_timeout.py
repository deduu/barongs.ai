from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from src.applications.search_agent.agents.web_researcher import WebResearcherAgent
from src.core.models.context import AgentContext
from src.core.models.results import ToolResult


def _make_agent(
    search_delay: float = 0.0,
    fetch_delay: float = 0.0,
    tool_timeout: float = 15.0,
) -> WebResearcherAgent:
    search_results = [
        {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1"},
    ]

    async def slow_search(_input):
        await asyncio.sleep(search_delay)
        return ToolResult(tool_name="brave_search", output=search_results)

    async def slow_fetch(_input):
        await asyncio.sleep(fetch_delay)
        return ToolResult(tool_name="content_fetcher", output="Page content")

    mock_search = AsyncMock()
    mock_search.name = "brave_search"
    mock_search.execute = AsyncMock(side_effect=slow_search)

    mock_fetcher = AsyncMock()
    mock_fetcher.name = "content_fetcher"
    mock_fetcher.execute = AsyncMock(side_effect=slow_fetch)

    mock_validator = AsyncMock()
    mock_validator.name = "url_validator"
    mock_validator.execute = AsyncMock(
        return_value=ToolResult(
            tool_name="url_validator",
            output=["https://example.com/1"],
        )
    )

    return WebResearcherAgent(
        search_tool=mock_search,
        content_fetcher=mock_fetcher,
        url_validator=mock_validator,
        max_sources=5,
        tool_timeout_seconds=tool_timeout,
    )


class TestWebResearcherTimeout:
    async def test_completes_within_timeout(self):
        agent = _make_agent(search_delay=0.0, fetch_delay=0.0, tool_timeout=5.0)
        ctx = AgentContext(user_message="test query")
        result = await agent.run(ctx)
        assert len(result.metadata["sources"]) == 1

    async def test_search_timeout_returns_empty(self):
        """If search tools timeout, agent returns gracefully with no sources."""
        agent = _make_agent(search_delay=2.0, tool_timeout=0.1)
        ctx = AgentContext(user_message="test query")
        result = await agent.run(ctx)
        assert result.metadata["sources"] == []

    async def test_fetch_timeout_returns_empty_content(self):
        """If content fetching times out, agent returns sources with empty content."""
        agent = _make_agent(fetch_delay=2.0, tool_timeout=0.1)
        ctx = AgentContext(user_message="test query")
        result = await agent.run(ctx)
        sources = result.metadata["sources"]
        assert len(sources) == 1
        assert sources[0]["content"] == ""
