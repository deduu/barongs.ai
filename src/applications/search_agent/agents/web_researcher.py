from __future__ import annotations

import asyncio
from typing import Any

from src.core.interfaces.agent import Agent
from src.core.interfaces.tool import Tool
from src.core.models.context import AgentContext, ToolInput
from src.core.models.results import AgentResult


class WebResearcherAgent(Agent):
    """Executes web searches, fetches content, and compiles sources."""

    def __init__(
        self,
        search_tool: Tool,
        content_fetcher: Tool,
        url_validator: Tool,
        max_sources: int = 5,
    ) -> None:
        self._search_tool = search_tool
        self._content_fetcher = content_fetcher
        self._url_validator = url_validator
        self._max_sources = max_sources

    @property
    def name(self) -> str:
        return "web_researcher"

    @property
    def description(self) -> str:
        return "Searches the web and compiles sources with content."

    async def run(self, context: AgentContext) -> AgentResult:
        refined_queries: list[str] = context.metadata.get("refined_queries", [context.user_message])

        # Step 1: Search for each refined query in parallel
        search_tasks = [
            self._search_tool.execute(
                ToolInput(tool_name=self._search_tool.name, parameters={"query": q})
            )
            for q in refined_queries
        ]
        search_results = await asyncio.gather(*search_tasks)

        # Collect all raw results
        all_results: list[dict[str, str]] = []
        for result in search_results:
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

        # Step 3: Fetch content for top N valid URLs in parallel
        top_urls = valid_urls[: self._max_sources]
        fetch_tasks = [
            self._content_fetcher.execute(
                ToolInput(tool_name=self._content_fetcher.name, parameters={"url": url})
            )
            for url in top_urls
        ]
        fetch_results = await asyncio.gather(*fetch_tasks)

        # Step 4: Compile sources with citation indices
        sources: list[dict[str, Any]] = []
        for i, (url, fetch_result) in enumerate(zip(top_urls, fetch_results, strict=True), start=1):
            original = url_to_result.get(url, {})
            sources.append(
                {
                    "url": url,
                    "title": original.get("title", ""),
                    "snippet": original.get("snippet", ""),
                    "content": fetch_result.output if fetch_result.success else "",
                    "index": i,
                }
            )

        return AgentResult(
            agent_name=self.name,
            response=f"Found {len(sources)} sources.",
            metadata={"sources": sources},
        )
