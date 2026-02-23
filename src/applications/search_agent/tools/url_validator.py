from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from src.core.interfaces.tool import Tool
from src.core.models.context import ToolInput
from src.core.models.results import ToolResult


class URLValidatorTool(Tool):
    """Validate, normalize, and deduplicate a list of URLs."""

    ALLOWED_SCHEMES = {"http", "https"}

    @property
    def name(self) -> str:
        return "url_validator"

    @property
    def description(self) -> str:
        return "Validate, normalize, and deduplicate a list of URLs."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to validate",
                },
            },
            "required": ["urls"],
        }

    @staticmethod
    def _normalize(url: str) -> str:
        """Normalize a URL by stripping trailing slash."""
        return url.rstrip("/")

    @staticmethod
    def _is_valid(url: str) -> bool:
        """Check if a URL has a valid scheme and netloc."""
        try:
            parsed = urlparse(url)
            return parsed.scheme in URLValidatorTool.ALLOWED_SCHEMES and bool(parsed.netloc)
        except Exception:
            return False

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        urls: list[str] = tool_input.parameters.get("urls", [])

        seen: set[str] = set()
        valid_urls: list[str] = []

        for url in urls:
            if not self._is_valid(url):
                continue
            normalized = self._normalize(url)
            if normalized not in seen:
                seen.add(normalized)
                valid_urls.append(normalized)

        return ToolResult(tool_name=self.name, output=valid_urls)
