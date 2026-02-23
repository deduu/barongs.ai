from __future__ import annotations

from typing import Any

import httpx
from bs4 import BeautifulSoup

from src.core.interfaces.tool import Tool
from src.core.middleware.circuit_breaker import CircuitBreaker
from src.core.models.context import ToolInput
from src.core.models.results import ToolResult


class ContentFetcherTool(Tool):
    """Fetch a URL and extract readable text content."""

    TAGS_TO_REMOVE = {"script", "style", "nav", "footer", "header", "aside", "noscript"}

    def __init__(
        self,
        timeout: float = 10.0,
        max_content_length: int = 5000,
    ) -> None:
        self._timeout = timeout
        self._max_content_length = max_content_length
        self._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    @property
    def name(self) -> str:
        return "content_fetcher"

    @property
    def description(self) -> str:
        return "Fetch a URL and extract readable text content from the HTML."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "format": "uri", "description": "URL to fetch"},
            },
            "required": ["url"],
        }

    def _extract_text(self, html: str) -> str:
        """Extract readable text from HTML, removing scripts and noise."""
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.find_all(self.TAGS_TO_REMOVE):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Collapse multiple blank lines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = "\n".join(lines)
        return cleaned[: self._max_content_length]

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        url = tool_input.parameters["url"]

        async def _fetch() -> str:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    timeout=self._timeout,
                    follow_redirects=True,
                    headers={"User-Agent": "Pormetheus/1.0"},
                )
                response.raise_for_status()
                return self._extract_text(response.text)

        try:
            content = await self._circuit_breaker.call(_fetch)
            return ToolResult(tool_name=self.name, output=content)
        except Exception as exc:
            return ToolResult(tool_name=self.name, output=None, success=False, error=str(exc))
