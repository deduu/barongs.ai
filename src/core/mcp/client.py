from __future__ import annotations

import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """Configuration for connecting to an MCP server."""

    name: str
    transport: str = "stdio"  # "stdio" | "sse"
    command: str | None = None  # For stdio transport
    args: list[str] = Field(default_factory=list)
    url: str | None = None  # For SSE transport
    env: dict[str, str] = Field(default_factory=dict)


class MCPClient:
    """Connects to an MCP server and exposes tool listing/calling.

    Uses the official mcp Python SDK for protocol compliance.

    Usage:
        client = MCPClient()
        await client.connect(MCPServerConfig(
            name="my-server",
            command="python",
            args=["-m", "my_mcp_server"],
        ))
        tools = await client.list_tools()
        result = await client.call_tool("search", {"query": "hello"})
        await client.disconnect()
    """

    def __init__(self) -> None:
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._config: MCPServerConfig | None = None

    @property
    def connected(self) -> bool:
        return self._session is not None

    async def connect(self, config: MCPServerConfig) -> None:
        """Connect to an MCP server using the specified configuration."""
        if self._session is not None:
            raise RuntimeError("Already connected. Call disconnect() first.")

        self._config = config
        self._exit_stack = AsyncExitStack()

        if config.transport == "stdio":
            if not config.command:
                raise ValueError("stdio transport requires 'command' to be set")

            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env if config.env else None,
            )
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(server_params, errlog=sys.stderr)
            )
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self._session.initialize()
        else:
            raise ValueError(f"Unsupported transport: {config.transport}")

    async def list_tools(self) -> list[dict[str, Any]]:
        """List all tools available on the connected MCP server."""
        if self._session is None:
            raise RuntimeError("Not connected. Call connect() first.")

        result = await self._session.list_tools()
        tools: list[dict[str, Any]] = []
        for tool in result.tools:
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.inputSchema if tool.inputSchema else {},
                }
            )
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the connected MCP server."""
        if self._session is None:
            raise RuntimeError("Not connected. Call connect() first.")

        result = await self._session.call_tool(name, arguments)
        # Extract text content from the result
        contents: list[str] = []
        for content_block in result.content:
            if hasattr(content_block, "text"):
                contents.append(content_block.text)
        return "\n".join(contents) if contents else str(result.content)

    async def disconnect(self) -> None:
        """Disconnect from the MCP server and clean up resources."""
        if self._exit_stack is not None:
            await self._exit_stack.aclose()
        self._session = None
        self._exit_stack = None
        self._config = None
