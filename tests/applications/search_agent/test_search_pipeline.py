from __future__ import annotations

from unittest.mock import AsyncMock

from src.applications.search_agent.agents.search_pipeline import SearchPipelineAgent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult


class TestSearchPipelineAgent:
    def _make_pipeline(
        self, *, query_type: str = "search"
    ) -> SearchPipelineAgent:
        # Mock QueryAnalyzer
        mock_analyzer = AsyncMock()
        mock_analyzer.name = "query_analyzer"
        mock_analyzer.run = AsyncMock(
            return_value=AgentResult(
                agent_name="query_analyzer",
                response="",
                metadata={
                    "query_type": query_type,
                    "refined_queries": ["refined query 1", "refined query 2"],
                },
            )
        )

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

        # Mock DirectAnswerer
        mock_direct = AsyncMock()
        mock_direct.name = "direct_answerer"
        mock_direct.run = AsyncMock(
            return_value=AgentResult(
                agent_name="direct_answerer",
                response="Direct answer.",
            )
        )

        return SearchPipelineAgent(
            query_analyzer=mock_analyzer,
            web_researcher=mock_researcher,
            synthesizer=mock_synthesizer,
            direct_answerer=mock_direct,
        )

    def test_name(self):
        pipeline = self._make_pipeline()
        assert pipeline.name == "search_pipeline"

    async def test_search_path(self):
        pipeline = self._make_pipeline(query_type="search")
        ctx = AgentContext(user_message="What is quantum computing?")
        result = await pipeline.run(ctx)

        assert "[1]" in result.response
        assert result.agent_name == "search_pipeline"
        assert "sources" in result.metadata
        assert result.metadata["query_type"] == "search"

    async def test_calls_query_analyzer_then_researcher_then_synthesizer(self):
        pipeline = self._make_pipeline()
        ctx = AgentContext(user_message="test query")
        await pipeline.run(ctx)

        pipeline._query_analyzer.run.assert_awaited_once()
        pipeline._web_researcher.run.assert_awaited_once()
        pipeline._synthesizer.run.assert_awaited_once()
        pipeline._direct_answerer.run.assert_not_awaited()

    async def test_direct_answer_path(self):
        pipeline = self._make_pipeline(query_type="direct")
        ctx = AgentContext(user_message="Hello!")
        result = await pipeline.run(ctx)

        assert result.response == "Direct answer."
        assert result.metadata["query_type"] == "direct"
        pipeline._direct_answerer.run.assert_awaited_once()
        pipeline._web_researcher.run.assert_not_awaited()
        pipeline._synthesizer.run.assert_not_awaited()

    async def test_passes_refined_queries_to_researcher(self):
        pipeline = self._make_pipeline()
        ctx = AgentContext(user_message="What is Python?")
        await pipeline.run(ctx)

        researcher_ctx = pipeline._web_researcher.run.call_args[0][0]
        assert researcher_ctx.metadata["refined_queries"] == [
            "refined query 1",
            "refined query 2",
        ]

    async def test_metadata_contains_sources(self):
        pipeline = self._make_pipeline()
        ctx = AgentContext(user_message="test")
        result = await pipeline.run(ctx)

        assert len(result.metadata["sources"]) == 1
        assert result.metadata["sources"][0]["url"] == "https://example.com"
