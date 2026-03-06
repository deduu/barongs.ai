from __future__ import annotations

from unittest.mock import AsyncMock

from src.applications.deep_search.agents.academic_researcher import AcademicResearcherAgent
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext
from src.core.models.results import ToolResult


class TestAcademicResearcherAgent:
    def test_name(self):
        agent = AcademicResearcherAgent(
            llm_provider=AsyncMock(),
            academic_search_tool=AsyncMock(),
            source_scorer_tool=AsyncMock(),
        )
        assert agent.name == "academic_researcher"

    async def test_searches_and_produces_findings(self):
        academic_tool = AsyncMock()
        academic_tool.name = "academic_search"
        academic_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="academic_search",
            output=[
                {
                    "title": "Deep Learning",
                    "url": "https://arxiv.org/abs/1",
                    "abstract": "A survey of deep learning techniques.",
                    "authors": ["Y. LeCun"],
                    "year": 2015,
                    "citation_count": 500,
                    "source": "arxiv",
                },
            ],
        ))

        scorer_tool = AsyncMock()
        scorer_tool.name = "source_scorer"
        scorer_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="source_scorer",
            output={
                "domain_authority": 0.9,
                "recency_score": 0.5,
                "citation_count": 500,
                "is_peer_reviewed": True,
                "overall_score": 0.85,
            },
        ))

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content="Deep learning is a subset of machine learning.",
            model="test", usage={"total_tokens": 50},
        ))

        agent = AcademicResearcherAgent(
            llm_provider=llm,
            academic_search_tool=academic_tool,
            source_scorer_tool=scorer_tool,
        )
        context = AgentContext(user_message="What is deep learning?")
        result = await agent.run(context)

        assert result.agent_name == "academic_researcher"
        assert "findings" in result.metadata
        assert len(result.metadata["findings"]) >= 1
        assert len(result.metadata["attempted_sources"]) == 1
        assert result.metadata["attempted_sources"][0]["status"] == "finding_extracted"
        called_params = academic_tool.execute.call_args.args[0].parameters
        assert called_params["query"] == "What is deep learning?"
        assert called_params["query_variants"][0] == "What is deep learning?"
        assert "google_scholar_web" in called_params["sources"]

    async def test_no_results_returns_empty_findings(self):
        academic_tool = AsyncMock()
        academic_tool.name = "academic_search"
        academic_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="academic_search", output=[],
        ))

        scorer_tool = AsyncMock()
        scorer_tool.name = "source_scorer"

        agent = AcademicResearcherAgent(
            llm_provider=AsyncMock(),
            academic_search_tool=academic_tool,
            source_scorer_tool=scorer_tool,
        )
        context = AgentContext(user_message="obscure query")
        result = await agent.run(context)

        assert result.metadata["findings"] == []

    async def test_retries_when_exact_entity_name_is_present(self):
        academic_tool = AsyncMock()
        academic_tool.name = "academic_search"
        academic_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="academic_search",
            output=[
                {
                    "title": "OpenClaw Safety Analysis",
                    "url": "https://example.org/openclaw-paper",
                    "abstract": "OpenClaw safety analysis for industrial use.",
                    "authors": ["A. Researcher"],
                    "year": 2024,
                    "citation_count": 5,
                    "source": "semantic_scholar",
                },
            ],
        ))

        scorer_tool = AsyncMock()
        scorer_tool.name = "source_scorer"
        scorer_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="source_scorer",
            output={"overall_score": 0.7},
        ))

        llm = AsyncMock()
        llm.generate = AsyncMock(side_effect=[
            LLMResponse(content="NOT_RELEVANT", model="test", usage={"total_tokens": 10}),
            LLMResponse(content="The paper discusses OpenClaw safety controls.", model="test", usage={"total_tokens": 20}),
        ])

        agent = AcademicResearcherAgent(
            llm_provider=llm,
            academic_search_tool=academic_tool,
            source_scorer_tool=scorer_tool,
        )
        context = AgentContext(
            user_message="go and search about OpenClaw safety and risk concern",
            metadata={"entity_grounding": {"name": "OpenClaw", "description": "A robotics system"}},
        )
        result = await agent.run(context)

        assert len(result.metadata["findings"]) == 1
        assert result.metadata["attempted_sources"][0]["status"] == "finding_extracted_retry"
