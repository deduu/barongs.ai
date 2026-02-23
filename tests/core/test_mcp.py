from __future__ import annotations

import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.mcp.client import MCPClient, MCPServerConfig
from src.core.mcp.skills_loader import load_skills_md
from src.core.mcp.tool_adapter import MCPToolAdapter
from src.core.models.context import ToolInput

# --- MCPServerConfig Tests ---


class TestMCPServerConfig:
    def test_defaults(self):
        config = MCPServerConfig(name="test-server")
        assert config.transport == "stdio"
        assert config.command is None
        assert config.args == []
        assert config.env == {}

    def test_stdio_config(self):
        config = MCPServerConfig(
            name="my-server",
            command="python",
            args=["-m", "my_server"],
            env={"KEY": "value"},
        )
        assert config.name == "my-server"
        assert config.command == "python"
        assert config.args == ["-m", "my_server"]


# --- MCPClient Tests ---


class TestMCPClient:
    def test_initial_state(self):
        client = MCPClient()
        assert not client.connected

    async def test_disconnect_when_not_connected(self):
        client = MCPClient()
        # Should not raise
        await client.disconnect()
        assert not client.connected

    async def test_list_tools_when_not_connected(self):
        client = MCPClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.list_tools()

    async def test_call_tool_when_not_connected(self):
        client = MCPClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.call_tool("test", {})

    async def test_connect_requires_command_for_stdio(self):
        client = MCPClient()
        config = MCPServerConfig(name="test", transport="stdio")
        with pytest.raises(ValueError, match="command"):
            await client.connect(config)

    async def test_connect_rejects_unsupported_transport(self):
        client = MCPClient()
        config = MCPServerConfig(name="test", transport="websocket", command="cmd")
        with pytest.raises(ValueError, match="Unsupported transport"):
            await client.connect(config)

    async def test_connect_already_connected(self):
        client = MCPClient()
        # Manually set session to simulate connected state
        client._session = MagicMock()
        config = MCPServerConfig(name="test", command="python", args=[])
        with pytest.raises(RuntimeError, match="Already connected"):
            await client.connect(config)
        # Cleanup
        client._session = None

    async def test_list_tools_returns_formatted_list(self):
        client = MCPClient()

        mock_tool = MagicMock()
        mock_tool.name = "search"
        mock_tool.description = "Search the web"
        mock_tool.inputSchema = {"type": "object", "properties": {"query": {"type": "string"}}}

        mock_result = MagicMock()
        mock_result.tools = [mock_tool]

        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=mock_result)
        client._session = mock_session

        tools = await client.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "search"
        assert tools[0]["description"] == "Search the web"
        assert "properties" in tools[0]["input_schema"]

        client._session = None

    async def test_call_tool_extracts_text_content(self):
        client = MCPClient()

        mock_content = MagicMock()
        mock_content.text = "Search result text"

        mock_result = MagicMock()
        mock_result.content = [mock_content]

        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        client._session = mock_session

        result = await client.call_tool("search", {"query": "test"})
        assert result == "Search result text"

        client._session = None


# --- MCPToolAdapter Tests ---


class TestMCPToolAdapter:
    def _make_adapter(self) -> tuple[MCPToolAdapter, AsyncMock]:
        mock_client = AsyncMock(spec=MCPClient)
        adapter = MCPToolAdapter(
            mcp_client=mock_client,
            tool_name="test_tool",
            tool_description="A test tool",
            tool_input_schema={"type": "object", "properties": {"q": {"type": "string"}}},
        )
        return adapter, mock_client

    def test_properties(self):
        adapter, _ = self._make_adapter()
        assert adapter.name == "test_tool"
        assert adapter.description == "A test tool"
        assert "properties" in adapter.input_schema

    async def test_execute_success(self):
        adapter, mock_client = self._make_adapter()
        mock_client.call_tool = AsyncMock(return_value="tool output")

        tool_input = ToolInput(tool_name="test_tool", parameters={"q": "hello"})
        result = await adapter.execute(tool_input)

        assert result.success is True
        assert result.output == "tool output"
        assert result.tool_name == "test_tool"
        assert result.duration_ms >= 0
        mock_client.call_tool.assert_awaited_once_with("test_tool", {"q": "hello"})

    async def test_execute_failure(self):
        adapter, mock_client = self._make_adapter()
        mock_client.call_tool = AsyncMock(side_effect=RuntimeError("connection lost"))

        tool_input = ToolInput(tool_name="test_tool", parameters={"q": "hello"})
        result = await adapter.execute(tool_input)

        assert result.success is False
        assert result.error == "connection lost"
        assert result.output is None

    def test_from_mcp_tool_info(self):
        mock_client = AsyncMock(spec=MCPClient)
        tool_info = {
            "name": "web_search",
            "description": "Search the web",
            "input_schema": {"type": "object"},
        }
        adapter = MCPToolAdapter.from_mcp_tool_info(mock_client, tool_info)
        assert adapter.name == "web_search"
        assert adapter.description == "Search the web"

    def test_from_mcp_tool_info_missing_fields(self):
        mock_client = AsyncMock(spec=MCPClient)
        tool_info = {"name": "minimal"}
        adapter = MCPToolAdapter.from_mcp_tool_info(mock_client, tool_info)
        assert adapter.name == "minimal"
        assert adapter.description == ""
        assert adapter.input_schema == {}


# --- Skills Loader Tests ---


class TestSkillsLoader:
    def test_parse_skills_md(self):
        content = """## web_search
Search the web for information.

**Parameters:**
- `query` (string, required): The search query
- `max_results` (integer, optional): Maximum number of results

## calculator
Perform mathematical calculations.

**Parameters:**
- `expression` (string, required): Math expression to evaluate
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            skills = load_skills_md(f.name)

        assert len(skills) == 2
        assert skills[0]["name"] == "web_search"
        assert "Search the web" in skills[0]["description"]
        assert len(skills[0]["parameters"]) == 2
        assert skills[0]["parameters"][0]["name"] == "query"
        assert skills[0]["parameters"][0]["required"] is True
        assert skills[0]["parameters"][1]["name"] == "max_results"
        assert skills[0]["parameters"][1]["required"] is False

    def test_parse_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("")
            f.flush()
            skills = load_skills_md(f.name)
        assert skills == []

    def test_parse_no_parameters(self):
        content = """## simple_tool
A tool with no parameters.
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            skills = load_skills_md(f.name)

        assert len(skills) == 1
        assert skills[0]["name"] == "simple_tool"
        assert skills[0]["parameters"] == []

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_skills_md("/nonexistent/SKILLS.md")
