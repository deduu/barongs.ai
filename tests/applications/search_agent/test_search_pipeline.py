from __future__ import annotations

from unittest.mock import AsyncMock

from src.applications.search_agent.agents.search_pipeline import SearchPipelineAgent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult


class TestSearchPipelineAgent:
    def _make_pipeline(self) -> SearchPipelineAgent:
        # Mock QueryAnalyzer (kept in __init__ but no longer called)
        mock_analyzer = AsyncMock()
        mock_analyzer.name = "query_analyzer"

        # Mock WebResearcher
        mock_researcher = AsyncMock()
        mock_researcher.name = "web_researcher"
        mock_researcher.run = AsyncMock(
            return_value=AgentResult(
                agent_name="web_researcher",
                response="Research complete",
                metadata={
                    "sources": [
                        {
                            "url": "https://example.com",
                            "title": "Example",
                            "snippet": "snippet",
                            "content": "Full content",
                            "index": 1,
                        }
                    ]
                },
            )
        )

        # Mock Synthesizer
        mock_synthesizer = AsyncMock()
        mock_synthesizer.name = "synthesizer"
        mock_synthesizer.run = AsyncMock(
            return_value=AgentResult(
                agent_name="synthesizer",
                response="Synthesized answer with [1] citation.",
                metadata={
                    "sources": [
                        {
                            "url": "https://example.com",
                            "title": "Example",
                            "snippet": "snippet",
                            "content": "Full content",
                            "index": 1,
                        }
                    ]
                },
            )
        )

        # Mock DirectAnswerer (kept in __init__ but no longer called)
        mock_direct = AsyncMock()
        mock_direct.name = "direct_answerer"

        return SearchPipelineAgent(
            query_analyzer=mock_analyzer,
            web_researcher=mock_researcher,
            synthesizer=mock_synthesizer,
            direct_answerer=mock_direct,
        )

    def test_name(self):
        pipeline = self._make_pipeline()
        assert pipeline.name == "search_pipeline"

    async def test_always_searches(self):
        pipeline = self._make_pipeline()
        ctx = AgentContext(user_message="What is quantum computing?")
        result = await pipeline.run(ctx)

        assert "[1]" in result.response
        assert result.agent_name == "search_pipeline"
        assert "sources" in result.metadata
        assert result.metadata["query_type"] == "search"

    async def test_skips_query_analyzer(self):
        pipeline = self._make_pipeline()
        ctx = AgentContext(user_message="test query")
        await pipeline.run(ctx)

        # QueryAnalyzer and DirectAnswerer should NOT be called
        pipeline._query_analyzer.run.assert_not_awaited()
        pipeline._direct_answerer.run.assert_not_awaited()

        # WebResearcher and Synthesizer should be called
        pipeline._web_researcher.run.assert_awaited_once()
        pipeline._synthesizer.run.assert_awaited_once()

    async def test_passes_original_query_as_refined(self):
        pipeline = self._make_pipeline()
        ctx = AgentContext(user_message="What is Python?")
        result = await pipeline.run(ctx)

        assert result.metadata["refined_queries"] == ["What is Python?"]

    async def test_metadata_contains_sources(self):
        pipeline = self._make_pipeline()
        ctx = AgentContext(user_message="test")
        result = await pipeline.run(ctx)

        assert len(result.metadata["sources"]) == 1
        assert result.metadata["sources"][0]["url"] == "https://example.com"
