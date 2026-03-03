from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx

from src.applications.deep_search.tools.academic_search import AcademicSearchTool
from src.core.models.context import ToolInput


class TestAcademicSearchToolProperties:
    def test_name(self):
        tool = AcademicSearchTool()
        assert tool.name == "academic_search"

    def test_description(self):
        tool = AcademicSearchTool()
        assert "academic" in tool.description.lower()

    def test_input_schema(self):
        tool = AcademicSearchTool()
        assert "query" in tool.input_schema["properties"]


class TestAcademicSearchToolSemanticScholar:
    async def test_semantic_scholar_success(self):
        mock_pool = AsyncMock()
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        response.json.return_value = {
            "data": [
                {
                    "title": "Deep Learning",
                    "url": "https://api.semanticscholar.org/paper1",
                    "abstract": "A survey of deep learning",
                    "authors": [{"name": "Y. LeCun"}],
                    "year": 2015,
                    "citationCount": 500,
                },
            ]
        }
        mock_pool.get = AsyncMock(return_value=response)

        tool = AcademicSearchTool(http_client=mock_pool, max_results=5)
        tool_input = ToolInput(
            tool_name="academic_search",
            parameters={"query": "deep learning", "sources": ["semantic_scholar"]},
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        assert len(result.output) >= 1
        assert result.output[0]["title"] == "Deep Learning"
        assert result.output[0]["source"] == "semantic_scholar"

    async def test_semantic_scholar_empty(self):
        mock_pool = AsyncMock()
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        response.json.return_value = {"data": []}
        mock_pool.get = AsyncMock(return_value=response)

        tool = AcademicSearchTool(http_client=mock_pool)
        tool_input = ToolInput(
            tool_name="academic_search",
            parameters={"query": "nonexistent topic", "sources": ["semantic_scholar"]},
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        assert result.output == []


class TestAcademicSearchToolArxiv:
    async def test_arxiv_success(self):
        arxiv_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Attention Is All You Need</title>
            <id>http://arxiv.org/abs/1706.03762v7</id>
            <summary>The dominant sequence transduction models...</summary>
            <author><name>Ashish Vaswani</name></author>
            <published>2017-06-12T00:00:00Z</published>
          </entry>
        </feed>"""
        mock_pool = AsyncMock()
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        response.text = arxiv_xml
        mock_pool.get = AsyncMock(return_value=response)

        tool = AcademicSearchTool(http_client=mock_pool)
        tool_input = ToolInput(
            tool_name="academic_search",
            parameters={"query": "transformer architecture", "sources": ["arxiv"]},
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        assert len(result.output) >= 1
        assert result.output[0]["title"] == "Attention Is All You Need"
        assert result.output[0]["source"] == "arxiv"


class TestAcademicSearchToolFailure:
    async def test_circuit_breaker_on_failure(self):
        mock_pool = AsyncMock()
        mock_pool.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
        )

        tool = AcademicSearchTool(http_client=mock_pool)
        tool_input = ToolInput(
            tool_name="academic_search",
            parameters={"query": "test"},
        )
        result = await tool.execute(tool_input)

        assert result.success is False
        assert result.error is not None

    async def test_default_both_sources(self):
        """When no sources specified, queries both APIs."""
        mock_pool = AsyncMock()

        # Semantic Scholar response
        ss_response = MagicMock()
        ss_response.status_code = 200
        ss_response.raise_for_status = MagicMock()
        ss_response.json.return_value = {"data": []}

        # arXiv response
        arxiv_response = MagicMock()
        arxiv_response.status_code = 200
        arxiv_response.raise_for_status = MagicMock()
        arxiv_response.text = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'

        mock_pool.get = AsyncMock(side_effect=[ss_response, arxiv_response])

        tool = AcademicSearchTool(http_client=mock_pool)
        tool_input = ToolInput(
            tool_name="academic_search",
            parameters={"query": "test"},
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        assert mock_pool.get.call_count == 2
