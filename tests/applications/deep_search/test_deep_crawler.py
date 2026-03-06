from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx

from src.applications.deep_search.tools.deep_crawler import DeepCrawlerTool
from src.core.models.context import ToolInput


class TestDeepCrawlerToolProperties:
    def test_name(self):
        tool = DeepCrawlerTool()
        assert tool.name == "deep_crawler"

    def test_description(self):
        tool = DeepCrawlerTool()
        assert "crawl" in tool.description.lower()

    def test_input_schema(self):
        tool = DeepCrawlerTool()
        assert "url" in tool.input_schema["properties"]


class TestDeepCrawlerToolExecution:
    async def test_single_page_crawl(self):
        html = """<html><head><title>Test Page</title></head>
        <body><p>Hello world</p></body></html>"""

        mock_pool = AsyncMock()
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        response.text = html
        response.headers = {"content-type": "text/html"}
        mock_pool.get = AsyncMock(return_value=response)

        tool = DeepCrawlerTool(http_client=mock_pool, max_depth=0)
        tool_input = ToolInput(
            tool_name="deep_crawler",
            parameters={"url": "https://example.com"},
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        assert len(result.output["pages"]) == 1
        assert result.output["pages"][0]["url"] == "https://example.com"
        assert "Hello world" in result.output["pages"][0]["content"]

    async def test_bfs_depth_crawl(self):
        """Test BFS crawl follows links up to max_depth."""
        page1_html = """<html><head><title>Page 1</title></head>
        <body><a href="https://example.com/page2">Link</a></body></html>"""
        page2_html = """<html><head><title>Page 2</title></head>
        <body><p>Second page</p></body></html>"""

        mock_pool = AsyncMock()
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.raise_for_status = MagicMock()
        resp1.text = page1_html
        resp1.headers = {"content-type": "text/html"}

        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.raise_for_status = MagicMock()
        resp2.text = page2_html
        resp2.headers = {"content-type": "text/html"}

        mock_pool.get = AsyncMock(side_effect=[resp1, resp2])

        tool = DeepCrawlerTool(http_client=mock_pool, max_depth=1, max_pages=10)
        tool_input = ToolInput(
            tool_name="deep_crawler",
            parameters={"url": "https://example.com"},
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        assert len(result.output["pages"]) == 2
        assert result.output["links_followed"] >= 1

    async def test_max_pages_limit(self):
        """Test crawl stops after max_pages."""
        html = """<html><body>
        <a href="https://example.com/p1">1</a>
        <a href="https://example.com/p2">2</a>
        <a href="https://example.com/p3">3</a>
        </body></html>"""

        mock_pool = AsyncMock()
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        response.text = html
        response.headers = {"content-type": "text/html"}
        mock_pool.get = AsyncMock(return_value=response)

        tool = DeepCrawlerTool(http_client=mock_pool, max_depth=2, max_pages=2)
        tool_input = ToolInput(
            tool_name="deep_crawler",
            parameters={"url": "https://example.com"},
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        assert len(result.output["pages"]) <= 2

    async def test_filters_non_http_links(self):
        html = """<html><body>
        <a href="mailto:test@example.com">Email</a>
        <a href="javascript:void(0)">JS</a>
        <a href="https://example.com/valid">Valid</a>
        </body></html>"""

        mock_pool = AsyncMock()
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        response.text = html
        response.headers = {"content-type": "text/html"}
        mock_pool.get = AsyncMock(return_value=response)

        tool = DeepCrawlerTool(http_client=mock_pool, max_depth=1, max_pages=10)
        tool_input = ToolInput(
            tool_name="deep_crawler",
            parameters={"url": "https://example.com"},
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        # Should have followed only the valid https link
        urls_crawled = [p["url"] for p in result.output["pages"]]
        assert "mailto:test@example.com" not in urls_crawled

    async def test_per_call_overrides_depth_and_page_limits(self):
        page1_html = """<html><head><title>Page 1</title></head>
        <body><a href="https://example.com/page2">Link</a></body></html>"""
        page2_html = """<html><head><title>Page 2</title></head>
        <body><p>Second page</p></body></html>"""

        mock_pool = AsyncMock()
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.raise_for_status = MagicMock()
        resp1.text = page1_html
        resp1.headers = {"content-type": "text/html"}

        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.raise_for_status = MagicMock()
        resp2.text = page2_html
        resp2.headers = {"content-type": "text/html"}

        mock_pool.get = AsyncMock(side_effect=[resp1, resp2])

        tool = DeepCrawlerTool(http_client=mock_pool, max_depth=0, max_pages=1)
        tool_input = ToolInput(
            tool_name="deep_crawler",
            parameters={
                "url": "https://example.com",
                "max_depth": 1,
                "max_pages": 2,
                "page_timeout_seconds": 3,
            },
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        assert len(result.output["pages"]) == 2

    async def test_failure_returns_empty_pages(self):
        """When all fetches fail, return empty pages list (not a tool error)."""
        mock_pool = AsyncMock()
        mock_pool.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        tool = DeepCrawlerTool(http_client=mock_pool)
        tool_input = ToolInput(
            tool_name="deep_crawler",
            parameters={"url": "https://unreachable.example.com"},
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        assert result.output["pages"] == []

    async def test_no_http_client_returns_error(self):
        tool = DeepCrawlerTool()
        tool_input = ToolInput(
            tool_name="deep_crawler",
            parameters={"url": "https://example.com"},
        )
        result = await tool.execute(tool_input)

        assert result.success is False
        assert result.error is not None
