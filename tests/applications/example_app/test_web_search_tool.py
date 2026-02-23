"""Tests for WebSearchTool — TDD: written before implementation.
External HTTP is mocked — never hit real services."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx

from src.applications.example_app.tools.web_search_tool import WebSearchTool
from src.core.models.context import ToolInput


class TestWebSearchTool:
    async def test_tool_name(self):
        tool = WebSearchTool()
        assert tool.name == "web_search"

    async def test_has_description(self):
        tool = WebSearchTool()
        assert len(tool.description) > 0

    async def test_has_input_schema(self):
        tool = WebSearchTool()
        schema = tool.input_schema
        assert "url" in schema["properties"]

    async def test_successful_fetch(self):
        tool = WebSearchTool()
        tool_input = ToolInput(
            tool_name="web_search",
            parameters={"url": "https://example.com"},
        )

        mock_response = AsyncMock()
        mock_response.text = "Hello from example.com"
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await tool.execute(tool_input)

        assert result.success is True
        assert "Hello from example.com" in result.output

    async def test_failure_returns_error(self):
        tool = WebSearchTool()
        tool_input = ToolInput(
            tool_name="web_search",
            parameters={"url": "https://fail.example.com"},
        )

        with patch(
            "httpx.AsyncClient.get",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            result = await tool.execute(tool_input)

        assert result.success is False
        assert result.error is not None
