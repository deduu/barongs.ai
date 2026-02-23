from __future__ import annotations

from typing import Any

import httpx

from src.core.interfaces.tool import Tool
from src.core.middleware.circuit_breaker import CircuitBreaker
from src.core.models.context import ToolInput
from src.core.models.results import ToolResult


class WebSearchTool(Tool):
    """Demo tool that performs an HTTP GET request."""

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout
        self._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Fetch content from a URL via HTTP GET."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"url": {"type": "string", "format": "uri"}},
            "required": ["url"],
        }

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        url = tool_input.parameters["url"]

        async def _fetch() -> str:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=self._timeout)
                resp.raise_for_status()
                return resp.text[:1000]

        try:
            content = await self._circuit_breaker.call(_fetch)
            return ToolResult(tool_name=self.name, output=content)
        except Exception as exc:
            return ToolResult(tool_name=self.name, output=None, success=False, error=str(exc))
