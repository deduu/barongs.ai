from __future__ import annotations

import time
from typing import Any

from src.core.interfaces.tool import Tool
from src.core.mcp.client import MCPClient
from src.core.models.context import ToolInput
from src.core.models.results import ToolResult


class MCPToolAdapter(Tool):
    """Wraps an MCP server tool as a barongsai Tool instance.

    This adapter translates between the barongsai Tool interface and MCP tool calls,
    allowing MCP tools to be used seamlessly within the agent framework.
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        tool_name: str,
        tool_description: str,
        tool_input_schema: dict[str, Any],
    ) -> None:
        self._mcp_client = mcp_client
        self._tool_name = tool_name
        self._tool_description = tool_description
        self._tool_input_schema = tool_input_schema

    @property
    def name(self) -> str:
        return self._tool_name

    @property
    def description(self) -> str:
        return self._tool_description

    @property
    def input_schema(self) -> dict[str, Any]:
        return self._tool_input_schema

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        start = time.monotonic()
        try:
            output = await self._mcp_client.call_tool(self._tool_name, tool_input.parameters)
            duration_ms = (time.monotonic() - start) * 1000
            return ToolResult(
                tool_name=self.name,
                output=output,
                success=True,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            return ToolResult(
                tool_name=self.name,
                output=None,
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
            )

    @classmethod
    def from_mcp_tool_info(
        cls,
        mcp_client: MCPClient,
        tool_info: dict[str, Any],
    ) -> MCPToolAdapter:
        """Create an adapter from an MCP tool info dict (as returned by MCPClient.list_tools)."""
        return cls(
            mcp_client=mcp_client,
            tool_name=tool_info["name"],
            tool_description=tool_info.get("description", ""),
            tool_input_schema=tool_info.get("input_schema", {}),
        )
