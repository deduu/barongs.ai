from __future__ import annotations

from unittest.mock import AsyncMock

from src.applications.deep_search.agents.deep_web_researcher import DeepWebResearcherAgent
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext
from src.core.models.results import ToolResult


class TestDeepWebResearcherAgent:
    def test_name(self):
        agent = DeepWebResearcherAgent(
            llm_provider=AsyncMock(),
            search_tool=AsyncMock(),
            deep_crawler_tool=AsyncMock(),
            source_scorer_tool=AsyncMock(),
        )
        assert agent.name == "deep_web_researcher"

    async def test_search_and_crawl_produces_findings(self):
        search_tool = AsyncMock()
        search_tool.name = "search"
        search_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="search",
            output=[
                {"title": "Python Guide", "url": "https://example.com/python", "snippet": "Guide"},
            ],
        ))

        crawler_tool = AsyncMock()
        crawler_tool.name = "deep_crawler"
        crawler_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="deep_crawler",
            output={
                "pages": [
                    {"url": "https://example.com/python", "title": "Python Guide", "content": "Python is great", "depth": 0},
                ],
                "links_followed": 0,
            },
        ))

        scorer_tool = AsyncMock()
        scorer_tool.name = "source_scorer"
        scorer_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="source_scorer",
            output={"domain_authority": 0.5, "recency_score": 0.5, "overall_score": 0.5, "citation_count": 0, "is_peer_reviewed": False},
        ))

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content="Python is a programming language.", model="test", usage={"total_tokens": 50},
        ))

        agent = DeepWebResearcherAgent(
            llm_provider=llm,
            search_tool=search_tool,
            deep_crawler_tool=crawler_tool,
            source_scorer_tool=scorer_tool,
        )
        context = AgentContext(user_message="What is Python?")
        result = await agent.run(context)

        assert result.agent_name == "deep_web_researcher"
        assert "findings" in result.metadata

    async def test_no_search_results_returns_empty(self):
        search_tool = AsyncMock()
        search_tool.name = "search"
        search_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="search", output=[],
        ))

        crawler = AsyncMock()
        crawler.name = "deep_crawler"
        scorer = AsyncMock()
        scorer.name = "source_scorer"

        agent = DeepWebResearcherAgent(
            llm_provider=AsyncMock(),
            search_tool=search_tool,
            deep_crawler_tool=crawler,
            source_scorer_tool=scorer,
        )
        context = AgentContext(user_message="obscure")
        result = await agent.run(context)

        assert result.metadata["findings"] == []

    async def test_filters_irrelevant_findings_via_not_relevant(self):
        """When LLM returns NOT_RELEVANT, that finding should be excluded."""
        search_tool = AsyncMock()
        search_tool.name = "search"
        search_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="search",
            output=[
                {"title": "Auditi.de", "url": "https://auditi.de", "snippet": "German company"},
                {"title": "Auditi CLI", "url": "https://github.com/deduu/auditi", "snippet": "CLI tool"},
            ],
        ))

        crawler_tool = AsyncMock()
        crawler_tool.name = "deep_crawler"
        crawler_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="deep_crawler",
            output={"pages": [{"content": "some content", "depth": 0}], "links_followed": 0},
        ))

        scorer_tool = AsyncMock()
        scorer_tool.name = "source_scorer"
        scorer_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="source_scorer", output={"overall_score": 0.5},
        ))

        call_count = 0

        async def mock_generate(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return LLMResponse(content="NOT_RELEVANT", model="test", usage={"total_tokens": 10})
            return LLMResponse(content="Auditi is a CLI tool for auditing.", model="test", usage={"total_tokens": 50})

        llm = AsyncMock()
        llm.generate = AsyncMock(side_effect=mock_generate)

        agent = DeepWebResearcherAgent(
            llm_provider=llm,
            search_tool=search_tool,
            deep_crawler_tool=crawler_tool,
            source_scorer_tool=scorer_tool,
        )
        context = AgentContext(
            user_message="What is Auditi?",
            metadata={"entity_grounding": {
                "name": "Auditi",
                "description": "A Python CLI for GitHub auditing by deduu",
            }},
        )
        result = await agent.run(context)

        assert len(result.metadata["findings"]) == 1
        assert "CLI tool" in result.metadata["findings"][0]["content"]

    async def test_entity_grounding_included_in_extraction_prompt(self):
        search_tool = AsyncMock()
        search_tool.name = "search"
        search_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="search",
            output=[{"title": "Page", "url": "https://example.com", "snippet": "snippet"}],
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

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(content="Finding.", model="test", usage={"total_tokens": 10}))

        agent = DeepWebResearcherAgent(
            llm_provider=llm, search_tool=search_tool,
            deep_crawler_tool=crawler_tool, source_scorer_tool=scorer_tool,
        )
        context = AgentContext(
            user_message="test",
            metadata={"entity_grounding": {"name": "MyEntity", "description": "A specific tool"}},
        )
        await agent.run(context)

        call_args = llm.generate.call_args[0][0]
        assert "MyEntity" in call_args.messages[0].content

    async def test_works_without_entity_grounding(self):
        search_tool = AsyncMock()
        search_tool.name = "search"
        search_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="search",
            output=[{"title": "Page", "url": "https://example.com", "snippet": "s"}],
        ))

        crawler_tool = AsyncMock()
        crawler_tool.name = "deep_crawler"
        crawler_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="deep_crawler",
            output={"pages": [{"content": "c", "depth": 0}], "links_followed": 0},
        ))

        scorer_tool = AsyncMock()
        scorer_tool.name = "source_scorer"
        scorer_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="source_scorer", output={"overall_score": 0.5},
        ))

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(content="Finding.", model="test", usage={"total_tokens": 10}))

        agent = DeepWebResearcherAgent(
            llm_provider=llm, search_tool=search_tool,
            deep_crawler_tool=crawler_tool, source_scorer_tool=scorer_tool,
        )
        context = AgentContext(user_message="test")
        result = await agent.run(context)

        assert len(result.metadata["findings"]) == 1
