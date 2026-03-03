from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.core.models.context import ToolInput
from src.core.tools.web.brave_search import BraveSearchTool
from src.core.tools.web.content_fetcher import ContentFetcherTool
from src.core.tools.web.duckduckgo_search import DuckDuckGoSearchTool

# --- Brave Search Tool Tests ---


class TestBraveSearchTool:
    def test_properties(self) -> None:
        tool = BraveSearchTool(api_key="test-key")
        assert tool.name == "brave_search"
        assert "search" in tool.description.lower()
        assert "query" in tool.input_schema["properties"]

    @patch("src.core.tools.web.brave_search.httpx.AsyncClient")
    async def test_search_success(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "Python Guide",
                        "url": "https://example.com/python",
                        "description": "A guide to Python programming",
                    },
                    {
                        "title": "Python Docs",
                        "url": "https://docs.python.org",
                        "description": "Official Python documentation",
                    },
                ]
            }
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        tool = BraveSearchTool(api_key="test-key")
        tool_input = ToolInput(tool_name="brave_search", parameters={"query": "Python"})
        result = await tool.execute(tool_input)

        assert result.success is True
        assert isinstance(result.output, list)
        assert len(result.output) == 2
        assert result.output[0]["title"] == "Python Guide"

    @patch("src.core.tools.web.brave_search.httpx.AsyncClient")
    async def test_search_failure(self, mock_client_cls: MagicMock) -> None:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        tool = BraveSearchTool(api_key="test-key")
        tool_input = ToolInput(tool_name="brave_search", parameters={"query": "test"})
        result = await tool.execute(tool_input)

        assert result.success is False
        assert result.error is not None

    @patch("src.core.tools.web.brave_search.httpx.AsyncClient")
    async def test_search_with_max_results(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"web": {"results": []}}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        tool = BraveSearchTool(api_key="test-key", max_results=5)
        tool_input = ToolInput(tool_name="brave_search", parameters={"query": "test"})
        await tool.execute(tool_input)

        call_kwargs = mock_client.get.call_args
        assert call_kwargs[1]["params"]["count"] == 5


# --- DuckDuckGo Search Tool Tests ---


class TestDuckDuckGoSearchTool:
    def test_properties(self) -> None:
        tool = DuckDuckGoSearchTool()
        assert tool.name == "duckduckgo_search"
        assert "search" in tool.description.lower()
        assert "query" in tool.input_schema["properties"]

    @patch("src.core.tools.web.duckduckgo_search.DDGS")
    async def test_search_success(self, mock_ddgs_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_instance.text.return_value = [
            {
                "title": "Python Guide",
                "href": "https://example.com/python",
                "body": "A guide to Python programming",
            },
            {
                "title": "Python Docs",
                "href": "https://docs.python.org",
                "body": "Official Python documentation",
            },
        ]
        mock_ddgs_cls.return_value = mock_instance

        tool = DuckDuckGoSearchTool(max_results=5)
        tool_input = ToolInput(tool_name="duckduckgo_search", parameters={"query": "Python"})
        result = await tool.execute(tool_input)

        assert result.success is True
        assert isinstance(result.output, list)
        assert len(result.output) == 2
        assert result.output[0]["title"] == "Python Guide"
        assert result.output[0]["url"] == "https://example.com/python"
        assert result.output[0]["snippet"] == "A guide to Python programming"

    @patch("src.core.tools.web.duckduckgo_search.DDGS")
    async def test_search_failure(self, mock_ddgs_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_instance.text.side_effect = Exception("DuckDuckGo rate limit")
        mock_ddgs_cls.return_value = mock_instance

        tool = DuckDuckGoSearchTool()
        tool_input = ToolInput(tool_name="duckduckgo_search", parameters={"query": "test"})
        result = await tool.execute(tool_input)

        assert result.success is False
        assert result.error is not None

    @patch("src.core.tools.web.duckduckgo_search.DDGS")
    async def test_search_empty_results(self, mock_ddgs_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_instance.text.return_value = []
        mock_ddgs_cls.return_value = mock_instance

        tool = DuckDuckGoSearchTool()
        tool_input = ToolInput(tool_name="duckduckgo_search", parameters={"query": "xyzzy"})
        result = await tool.execute(tool_input)

        assert result.success is True
        assert result.output == []


# --- Content Fetcher Tool Tests ---


class TestContentFetcherTool:
    def test_properties(self) -> None:
        tool = ContentFetcherTool()
        assert tool.name == "content_fetcher"
        assert "url" in tool.input_schema["properties"]

    @patch("src.core.tools.web.content_fetcher.httpx.AsyncClient")
    async def test_fetch_success(self, mock_client_cls: MagicMock) -> None:
        html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
        <h1>Main Heading</h1>
        <p>This is the main content of the page.</p>
        <script>console.log("should be removed")</script>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_response.headers = {"content-type": "text/html"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        tool = ContentFetcherTool()
        tool_input = ToolInput(
            tool_name="content_fetcher",
            parameters={"url": "https://example.com"},
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        assert "Main Heading" in result.output
        assert "main content" in result.output
        assert "console.log" not in result.output

    @patch("src.core.tools.web.content_fetcher.httpx.AsyncClient")
    async def test_fetch_failure(self, mock_client_cls: MagicMock) -> None:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        tool = ContentFetcherTool()
        tool_input = ToolInput(
            tool_name="content_fetcher",
            parameters={"url": "https://unreachable.example.com"},
        )
        result = await tool.execute(tool_input)

        assert result.success is False
        assert result.error is not None

    @patch("src.core.tools.web.content_fetcher.httpx.AsyncClient")
    async def test_content_truncation(self, mock_client_cls: MagicMock) -> None:
        long_text = "x" * 10000
        html = f"<html><body><p>{long_text}</p></body></html>"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_response.headers = {"content-type": "text/html"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        tool = ContentFetcherTool(max_content_length=500)
        tool_input = ToolInput(
            tool_name="content_fetcher",
            parameters={"url": "https://example.com"},
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        assert len(result.output) <= 500


# --- Re-export backward compatibility tests ---


class TestReExportBackwardCompat:
    """Verify tools are still importable from original search_agent paths."""

    def test_brave_search_importable_from_search_agent(self) -> None:
        from src.applications.search_agent.tools.search_api import BraveSearchTool as BraveSA

        assert BraveSA is BraveSearchTool

    def test_duckduckgo_importable_from_search_agent(self) -> None:
        from src.applications.search_agent.tools.search_api import DuckDuckGoSearchTool as DdgSA

        assert DdgSA is DuckDuckGoSearchTool

    def test_content_fetcher_importable_from_search_agent(self) -> None:
        from src.applications.search_agent.tools.content_fetcher import ContentFetcherTool as CfSA

        assert CfSA is ContentFetcherTool

    def test_importable_from_core_init(self) -> None:
        from src.core import BraveSearchTool as BraveCore
        from src.core import ContentFetcherTool as CfCore
        from src.core import DuckDuckGoSearchTool as DdgCore

        assert BraveCore is BraveSearchTool
        assert DdgCore is DuckDuckGoSearchTool
        assert CfCore is ContentFetcherTool
