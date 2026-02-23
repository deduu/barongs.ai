from __future__ import annotations

import asyncio
from typing import Any

import httpx
from ddgs import DDGS

from src.core.interfaces.tool import Tool
from src.core.middleware.circuit_breaker import CircuitBreaker
from src.core.models.context import ToolInput
from src.core.models.results import ToolResult


class BraveSearchTool(Tool):
    """Web search tool using the Brave Search API."""

    BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(
        self,
        api_key: str,
        max_results: int = 10,
        timeout: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._max_results = max_results
        self._timeout = timeout
        self._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    @property
    def name(self) -> str:
        return "brave_search"

    @property
    def description(self) -> str:
        return "Search the web using Brave Search API. Returns titles, URLs, and snippets."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
            },
            "required": ["query"],
        }

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        query = tool_input.parameters["query"]

        async def _search() -> list[dict[str, str]]:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BRAVE_API_URL,
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "X-Subscription-Token": self._api_key,
                    },
                    params={"q": query, "count": self._max_results},
                    timeout=self._timeout,
                )
                response.raise_for_status()
                data = response.json()

            results: list[dict[str, str]] = []
            for item in data.get("web", {}).get("results", []):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("description", ""),
                    }
                )
            return results

        try:
            output = await self._circuit_breaker.call(_search)
            return ToolResult(tool_name=self.name, output=output)
        except Exception as exc:
            return ToolResult(tool_name=self.name, output=None, success=False, error=str(exc))


class DuckDuckGoSearchTool(Tool):
    """Web search tool using DuckDuckGo. No API key required."""

    def __init__(self, max_results: int = 10) -> None:
        self._max_results = max_results
        self._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    @property
    def name(self) -> str:
        return "duckduckgo_search"

    @property
    def description(self) -> str:
        return "Search the web using DuckDuckGo. No API key required. Returns titles, URLs, and snippets."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
            },
            "required": ["query"],
        }

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        query = tool_input.parameters["query"]

        def _search_sync() -> list[dict[str, str]]:
            raw = DDGS().text(query, max_results=self._max_results)
            results: list[dict[str, str]] = []
            for item in raw:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("href", ""),
                        "snippet": item.get("body", ""),
                    }
                )
            return results

        async def _search() -> list[dict[str, str]]:
            return await asyncio.to_thread(_search_sync)

        try:
            output = await self._circuit_breaker.call(_search)
            return ToolResult(tool_name=self.name, output=output)
        except Exception as exc:
            return ToolResult(tool_name=self.name, output=None, success=False, error=str(exc))
