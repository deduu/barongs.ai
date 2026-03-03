from __future__ import annotations

from src.applications.deep_search.tools.source_scorer import SourceScorerTool
from src.core.models.context import ToolInput


class TestSourceScorerToolProperties:
    def test_name(self):
        tool = SourceScorerTool()
        assert tool.name == "source_scorer"

    def test_description(self):
        tool = SourceScorerTool()
        assert "scor" in tool.description.lower() or "credib" in tool.description.lower()

    def test_input_schema(self):
        tool = SourceScorerTool()
        assert "url" in tool.input_schema["properties"]


class TestSourceScorerToolScoring:
    async def test_gov_domain_high_authority(self):
        tool = SourceScorerTool()
        result = await tool.execute(ToolInput(
            tool_name="source_scorer",
            parameters={"url": "https://www.nih.gov/research", "year": 2025},
        ))

        assert result.success is True
        assert result.output["domain_authority"] >= 0.8

    async def test_edu_domain_high_authority(self):
        tool = SourceScorerTool()
        result = await tool.execute(ToolInput(
            tool_name="source_scorer",
            parameters={"url": "https://mit.edu/papers/test", "year": 2024},
        ))

        assert result.success is True
        assert result.output["domain_authority"] >= 0.8

    async def test_news_domain_medium_authority(self):
        tool = SourceScorerTool()
        result = await tool.execute(ToolInput(
            tool_name="source_scorer",
            parameters={"url": "https://www.reuters.com/article/test"},
        ))

        assert result.success is True
        assert 0.5 <= result.output["domain_authority"] <= 0.9

    async def test_blog_domain_lower_authority(self):
        tool = SourceScorerTool()
        result = await tool.execute(ToolInput(
            tool_name="source_scorer",
            parameters={"url": "https://random-blog.wordpress.com/post"},
        ))

        assert result.success is True
        assert result.output["domain_authority"] <= 0.5

    async def test_recency_score_recent(self):
        tool = SourceScorerTool()
        result = await tool.execute(ToolInput(
            tool_name="source_scorer",
            parameters={"url": "https://example.com", "year": 2026},
        ))

        assert result.success is True
        assert result.output["recency_score"] >= 0.8

    async def test_recency_score_old(self):
        tool = SourceScorerTool()
        result = await tool.execute(ToolInput(
            tool_name="source_scorer",
            parameters={"url": "https://example.com", "year": 2010},
        ))

        assert result.success is True
        assert result.output["recency_score"] < 0.5

    async def test_citation_count_boosts_score(self):
        tool = SourceScorerTool()
        # Low citations
        result_low = await tool.execute(ToolInput(
            tool_name="source_scorer",
            parameters={"url": "https://example.com", "citation_count": 0},
        ))
        # High citations
        result_high = await tool.execute(ToolInput(
            tool_name="source_scorer",
            parameters={"url": "https://example.com", "citation_count": 500},
        ))

        assert result_high.success is True
        assert result_high.output["overall_score"] > result_low.output["overall_score"]

    async def test_peer_reviewed_boosts_score(self):
        tool = SourceScorerTool()
        result = await tool.execute(ToolInput(
            tool_name="source_scorer",
            parameters={
                "url": "https://example.com",
                "is_peer_reviewed": True,
            },
        ))

        assert result.success is True
        assert result.output["is_peer_reviewed"] is True
        assert result.output["overall_score"] > 0.5

    async def test_overall_score_in_range(self):
        tool = SourceScorerTool()
        result = await tool.execute(ToolInput(
            tool_name="source_scorer",
            parameters={"url": "https://example.com"},
        ))

        assert result.success is True
        assert 0.0 <= result.output["overall_score"] <= 1.0
