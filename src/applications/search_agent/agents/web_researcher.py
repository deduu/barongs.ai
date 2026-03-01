from __future__ import annotations

import logging
from typing import Any

from src.core.interfaces.agent import Agent
from src.core.interfaces.tool import Tool
from src.core.models.context import AgentContext, ToolInput
from src.core.models.results import AgentResult, ToolResult
from src.core.utils.async_helpers import gather_with_timeout

logger = logging.getLogger(__name__)


class WebResearcherAgent(Agent):
    """Executes web searches, fetches content, and compiles sources."""

    def __init__(
        self,
        search_tool: Tool,
        content_fetcher: Tool,
        url_validator: Tool,
        max_sources: int = 8,
        tool_timeout_seconds: float = 15.0,
    ) -> None:
        self._search_tool = search_tool
        self._content_fetcher = content_fetcher
        self._url_validator = url_validator
        self._max_sources = max_sources
        self._tool_timeout = tool_timeout_seconds

    @property
    def name(self) -> str:
        return "web_researcher"

    @property
    def description(self) -> str:
        return "Searches the web and compiles sources with content."

    async def run(self, context: AgentContext) -> AgentResult:
        refined_queries: list[str] = context.metadata.get("refined_queries", [context.user_message])

        # Step 1: Search for each refined query in parallel (with timeout)
        search_tasks = [
            self._search_tool.execute(
                ToolInput(tool_name=self._search_tool.name, parameters={"query": q})
            )
            for q in refined_queries
        ]
        try:
            search_results = await gather_with_timeout(
                *search_tasks,
                timeout_seconds=self._tool_timeout,
                return_exceptions=True,
            )
        except TimeoutError:
            logger.warning("Search tools timed out after %ss", self._tool_timeout)
            search_results = []

        # Collect all raw results
        all_results: list[dict[str, str]] = []
        for result in search_results:
            if isinstance(result, BaseException):
                logger.warning("Search task failed: %s", result)
                continue
            if result.success and isinstance(result.output, list):
                all_results.extend(result.output)

        if not all_results:
            return AgentResult(
                agent_name=self.name,
                response="No search results found.",
                metadata={"sources": []},
            )

        # Step 2: Validate and deduplicate URLs
        urls = [r["url"] for r in all_results if r.get("url")]
        validation_result = await self._url_validator.execute(
            ToolInput(tool_name=self._url_validator.name, parameters={"urls": urls})
        )
        valid_urls: list[str] = validation_result.output if validation_result.success else urls

        # Build URL-to-result lookup
        url_to_result: dict[str, dict[str, str]] = {}
        for r in all_results:
            normalized = r.get("url", "").rstrip("/")
            if normalized not in url_to_result:
                url_to_result[normalized] = r

        # Step 3: Fetch content for top N valid URLs in parallel (with timeout)
        top_urls = valid_urls[: self._max_sources]
        fetch_tasks = [
            self._content_fetcher.execute(
                ToolInput(tool_name=self._content_fetcher.name, parameters={"url": url})
            )
            for url in top_urls
        ]
        try:
            fetch_results = await gather_with_timeout(
                *fetch_tasks,
                timeout_seconds=self._tool_timeout,
                return_exceptions=True,
            )
        except TimeoutError:
            logger.warning("Content fetching timed out after %ss", self._tool_timeout)
            fetch_results = [
                ToolResult(tool_name=self._content_fetcher.name, output="", success=False)
                for _ in top_urls
            ]

        # Step 4: Compile sources with citation indices
        sources: list[dict[str, Any]] = []
        for i, (url, fetch_result) in enumerate(zip(top_urls, fetch_results, strict=True), start=1):
            original = url_to_result.get(url, {})
            content = ""
            if not isinstance(fetch_result, BaseException) and fetch_result.success:
                content = fetch_result.output
            sources.append(
                {
                    "url": url,
                    "title": original.get("title", ""),
                    "snippet": original.get("snippet", ""),
                    "content": content,
                    "index": i,
                }
            )

        return AgentResult(
            agent_name=self.name,
            response=f"Found {len(sources)} sources.",
            metadata={"sources": sources},
        )
