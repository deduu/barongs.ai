from __future__ import annotations

import json
from unittest.mock import AsyncMock

from src.applications.search_agent.agents.query_analyzer import QueryAnalyzerAgent
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext


class TestQueryAnalyzerAgent:
    def _make_agent(self, llm_response_content: str) -> QueryAnalyzerAgent:
        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(
            return_value=LLMResponse(content=llm_response_content, model="gpt-4o")
        )
        return QueryAnalyzerAgent(llm_provider=mock_provider, model="gpt-4o")

    def test_name(self):
        agent = self._make_agent("{}")
        assert agent.name == "query_analyzer"

    async def test_classifies_search_query(self):
        response = json.dumps(
            {
                "query_type": "search",
                "refined_queries": ["latest Python 3.13 features", "Python 3.13 release notes"],
            }
        )
        agent = self._make_agent(response)
        ctx = AgentContext(user_message="What are the new features in Python 3.13?")
        result = await agent.run(ctx)

        assert result.metadata["query_type"] == "search"
        assert len(result.metadata["refined_queries"]) == 2

    async def test_classifies_direct_query(self):
        response = json.dumps(
            {
                "query_type": "direct",
                "refined_queries": [],
            }
        )
        agent = self._make_agent(response)
        ctx = AgentContext(user_message="Hello, how are you?")
        result = await agent.run(ctx)

        assert result.metadata["query_type"] == "direct"
        assert result.metadata["refined_queries"] == []

    async def test_handles_malformed_llm_response(self):
        agent = self._make_agent("this is not json")
        ctx = AgentContext(user_message="test query")
        result = await agent.run(ctx)

        # Should default to search when parsing fails
        assert result.metadata["query_type"] == "search"
        assert result.metadata["refined_queries"] == ["test query"]
