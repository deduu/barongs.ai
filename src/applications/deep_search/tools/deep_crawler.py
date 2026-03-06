from __future__ import annotations

import logging
from collections import deque
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from src.core.http.client import HttpClientPool
from src.core.interfaces.tool import Tool
from src.core.middleware.circuit_breaker import CircuitBreaker
from src.core.models.context import ToolInput
from src.core.models.results import ToolResult

logger = logging.getLogger(__name__)


class DeepCrawlerTool(Tool):
    """BFS recursive web crawler with depth and page limits."""

    def __init__(
        self,
        *,
        http_client: HttpClientPool | None = None,
        max_depth: int = 2,
        max_pages: int = 10,
    ) -> None:
        self._http_client = http_client
        self._max_depth = max_depth
        self._max_pages = max_pages
        self._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    @property
    def name(self) -> str:
        return "deep_crawler"

    @property
    def description(self) -> str:
        return "BFS crawl web pages recursively, extracting content and following links."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Starting URL to crawl"},
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to filter links (optional)",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Optional depth override for this crawl request",
                    "minimum": 0,
                    "maximum": 5,
                },
                "max_pages": {
                    "type": "integer",
                    "description": "Optional page limit override for this crawl request",
                    "minimum": 1,
                    "maximum": 30,
                },
                "page_timeout_seconds": {
                    "type": "number",
                    "description": "Optional per-page HTTP timeout in seconds",
                    "minimum": 1,
                    "maximum": 30,
                },
            },
            "required": ["url"],
        }

    def _extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:5000]

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        for a in soup.find_all("a", href=True):
            href: str = str(a["href"])
            full_url: str = urljoin(base_url, href)
            parsed = urlparse(full_url)
            if parsed.scheme in ("http", "https"):
                links.append(full_url)
        return links

    @staticmethod
    def _bounded_int(value: Any, default: int, *, min_value: int, max_value: int) -> int:
        if isinstance(value, int):
            return max(min_value, min(max_value, value))
        return default

    @staticmethod
    def _bounded_float(
        value: Any, default: float, *, min_value: float, max_value: float
    ) -> float:
        if isinstance(value, (int, float)):
            numeric = float(value)
            return max(min_value, min(max_value, numeric))
        return default

    async def _fetch_page(self, url: str) -> tuple[str, str]:
        """Fetch a page, return (title, content)."""
        assert self._http_client is not None
        response = await self._http_client.get(url, timeout=httpx.Timeout(10.0))
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else url
        content = self._extract_text(html)
        return title, content

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        start_url = tool_input.parameters["url"]
        max_depth = self._bounded_int(
            tool_input.parameters.get("max_depth"),
            self._max_depth,
            min_value=0,
            max_value=5,
        )
        max_pages = self._bounded_int(
            tool_input.parameters.get("max_pages"),
            self._max_pages,
            min_value=1,
            max_value=30,
        )
        page_timeout_seconds = self._bounded_float(
            tool_input.parameters.get("page_timeout_seconds"),
            10.0,
            min_value=1.0,
            max_value=30.0,
        )

        if self._http_client is None:
            return ToolResult(
                tool_name=self.name, output=None, success=False,
                error="No HTTP client configured",
            )

        http_client = self._http_client

        async def _crawl() -> dict[str, Any]:
            visited: set[str] = set()
            pages: list[dict[str, Any]] = []
            links_followed = 0

            # BFS queue: (url, depth)
            queue: deque[tuple[str, int]] = deque([(start_url, 0)])

            while queue and len(pages) < max_pages:
                url, depth = queue.popleft()
                normalized = url.rstrip("/")
                if normalized in visited:
                    continue
                visited.add(normalized)

                try:
                    response = await http_client.get(
                        url, timeout=httpx.Timeout(page_timeout_seconds)
                    )
                    response.raise_for_status()
                    html = response.text
                except httpx.TimeoutException:
                    logger.debug("Timeout fetching %s — skipping", url)
                    continue
                except Exception:
                    logger.debug("Failed to fetch %s", url)
                    continue

                soup = BeautifulSoup(html, "html.parser")
                title = soup.title.string.strip() if soup.title and soup.title.string else url
                content = self._extract_text(html)

                pages.append({
                    "url": url,
                    "title": title,
                    "content": content,
                    "depth": depth,
                })

                if depth < max_depth:
                    child_links = self._extract_links(html, url)
                    for link in child_links:
                        norm_link = link.rstrip("/")
                        if norm_link not in visited:
                            queue.append((link, depth + 1))
                            links_followed += 1

            return {"pages": pages, "links_followed": links_followed}

        try:
            output = await self._circuit_breaker.call(_crawl)
            return ToolResult(tool_name=self.name, output=output)
        except Exception as exc:
            return ToolResult(tool_name=self.name, output=None, success=False, error=str(exc))
