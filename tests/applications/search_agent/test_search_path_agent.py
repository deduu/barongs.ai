from __future__ import annotations

from unittest.mock import AsyncMock

from src.applications.search_agent.agents.search_path import SearchPathAgent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult


class TestSearchPathAgent:
    def _make_agent(self) -> SearchPathAgent:
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

        return SearchPathAgent(
            web_researcher=mock_researcher,
            synthesizer=mock_synthesizer,
            timeout_seconds=30.0,
        )

    def test_name(self):
        agent = self._make_agent()
        assert agent.name == "search_path"

    def test_description(self):
        agent = self._make_agent()
        assert "research" in agent.description.lower()

    async def test_delegates_to_internal_orchestrator(self):
        agent = self._make_agent()
        ctx = AgentContext(user_message="What is Python?")
        result = await agent.run(ctx)

        assert result.response == "Synthesized answer with [1] citation."
        assert "sources" in result.metadata

    async def test_metadata_flows_from_researcher_to_synthesizer(self):
        """PipelineWithMetadataStrategy should merge researcher metadata into synth context."""
        agent = self._make_agent()
        ctx = AgentContext(user_message="test query")
        result = await agent.run(ctx)

        # The final result should contain sources from the merged pipeline metadata
        assert "sources" in result.metadata
        assert len(result.metadata["sources"]) == 1
        assert result.metadata["sources"][0]["url"] == "https://example.com"
