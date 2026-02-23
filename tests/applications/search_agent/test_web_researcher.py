from __future__ import annotations

from unittest.mock import AsyncMock

from src.applications.search_agent.agents.web_researcher import WebResearcherAgent
from src.core.models.context import AgentContext
from src.core.models.results import ToolResult


class TestWebResearcherAgent:
    def _make_agent(
        self,
        search_results: list[dict[str, str]] | None = None,
        fetch_content: str = "Page content here",
    ) -> WebResearcherAgent:
        if search_results is None:
            search_results = [
                {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1"},
                {"title": "Result 2", "url": "https://example.com/2", "snippet": "Snippet 2"},
            ]

        mock_search_tool = AsyncMock()
        mock_search_tool.name = "brave_search"
        mock_search_tool.execute = AsyncMock(
            return_value=ToolResult(tool_name="brave_search", output=search_results)
        )

        mock_fetcher = AsyncMock()
        mock_fetcher.name = "content_fetcher"
        mock_fetcher.execute = AsyncMock(
            return_value=ToolResult(tool_name="content_fetcher", output=fetch_content)
        )

        mock_validator = AsyncMock()
        mock_validator.name = "url_validator"
        mock_validator.execute = AsyncMock(
            return_value=ToolResult(
                tool_name="url_validator",
                output=[r["url"] for r in search_results],
            )
        )

        return WebResearcherAgent(
            search_tool=mock_search_tool,
            content_fetcher=mock_fetcher,
            url_validator=mock_validator,
            max_sources=5,
        )

    def test_name(self):
        agent = self._make_agent()
        assert agent.name == "web_researcher"

    async def test_research_produces_sources(self):
        agent = self._make_agent()
        ctx = AgentContext(
            user_message="What is Python?",
            metadata={
                "refined_queries": ["What is Python programming language"],
            },
        )
        result = await agent.run(ctx)

        sources = result.metadata.get("sources", [])
        assert len(sources) == 2
        assert sources[0]["title"] == "Result 1"
        assert sources[0]["content"] == "Page content here"
        assert sources[0]["index"] == 1

    async def test_uses_original_query_when_no_refined(self):
        agent = self._make_agent()
        ctx = AgentContext(user_message="What is Python?")
        result = await agent.run(ctx)

        # Should still work, using the original message as the query
        sources = result.metadata.get("sources", [])
        assert len(sources) >= 1

    async def test_handles_empty_search_results(self):
        agent = self._make_agent(search_results=[])
        ctx = AgentContext(
            user_message="obscure query",
            metadata={"refined_queries": ["obscure query"]},
        )
        result = await agent.run(ctx)

        sources = result.metadata.get("sources", [])
        assert sources == []
