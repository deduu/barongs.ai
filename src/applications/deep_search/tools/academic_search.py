from __future__ import annotations

import asyncio
from typing import Any
from xml.etree import ElementTree

from ddgs import DDGS

from src.core.http.client import HttpClientPool
from src.core.interfaces.tool import Tool
from src.core.middleware.circuit_breaker import CircuitBreaker
from src.core.models.context import ToolInput
from src.core.models.results import ToolResult

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_URL = "http://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


class AcademicSearchTool(Tool):
    """Search academic papers via Semantic Scholar/arXiv and Scholar-indexed web results."""

    def __init__(
        self,
        *,
        http_client: HttpClientPool | None = None,
        max_results: int = 10,
        semantic_scholar_url: str = SEMANTIC_SCHOLAR_URL,
        arxiv_url: str = ARXIV_URL,
    ) -> None:
        self._http_client = http_client
        self._max_results = max_results
        self._ss_url = semantic_scholar_url
        self._arxiv_url = arxiv_url
        self._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    @property
    def name(self) -> str:
        return "academic_search"

    @property
    def description(self) -> str:
        return "Search academic papers from Semantic Scholar, arXiv, and Google Scholar-indexed web results."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Academic search query"},
                "query_variants": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional alternative query rewrites to improve recall.",
                },
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Sources to query: 'semantic_scholar', 'arxiv', 'google_scholar_web'. Default: semantic_scholar + arxiv.",
                },
            },
            "required": ["query"],
        }

    async def _search_semantic_scholar(self, query: str) -> list[dict[str, Any]]:
        params = {
            "query": query,
            "limit": self._max_results,
            "fields": "title,url,abstract,authors,year,citationCount",
        }
        assert self._http_client is not None
        response = await self._http_client.get(self._ss_url, params=params)
        response.raise_for_status()
        data = response.json()

        results: list[dict[str, Any]] = []
        for paper in data.get("data", []):
            authors = [a.get("name", "") for a in paper.get("authors", [])]
            results.append({
                "title": paper.get("title", ""),
                "url": paper.get("url", ""),
                "abstract": paper.get("abstract", ""),
                "authors": authors,
                "year": paper.get("year"),
                "citation_count": paper.get("citationCount", 0),
                "source": "semantic_scholar",
            })
        return results

    async def _search_arxiv(self, query: str) -> list[dict[str, Any]]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": self._max_results,
        }
        assert self._http_client is not None
        response = await self._http_client.get(self._arxiv_url, params=params)
        response.raise_for_status()

        root = ElementTree.fromstring(response.text)
        results: list[dict[str, Any]] = []
        for entry in root.findall("atom:entry", ARXIV_NS):
            title_el = entry.find("atom:title", ARXIV_NS)
            id_el = entry.find("atom:id", ARXIV_NS)
            summary_el = entry.find("atom:summary", ARXIV_NS)
            published_el = entry.find("atom:published", ARXIV_NS)

            authors = [
                a.find("atom:name", ARXIV_NS).text  # type: ignore[union-attr]
                for a in entry.findall("atom:author", ARXIV_NS)
                if a.find("atom:name", ARXIV_NS) is not None
            ]

            year = None
            if published_el is not None and published_el.text:
                year = int(published_el.text[:4])

            results.append({
                "title": title_el.text.strip() if title_el is not None and title_el.text else "",
                "url": id_el.text.strip() if id_el is not None and id_el.text else "",
                "abstract": (
                    summary_el.text.strip()
                    if summary_el is not None and summary_el.text
                    else ""
                ),
                "authors": authors,
                "year": year,
                "citation_count": 0,
                "source": "arxiv",
            })
        return results

    async def _search_google_scholar_web(self, query: str) -> list[dict[str, Any]]:
        """Best-effort Scholar web fallback via DDGS using site filter."""
        scholar_query = f"site:scholar.google.com {query}"

        def _search_sync() -> list[dict[str, Any]]:
            raw = DDGS().text(scholar_query, max_results=self._max_results)
            results: list[dict[str, Any]] = []
            for item in raw:
                title = item.get("title", "")
                url = item.get("href", "")
                snippet = item.get("body", "")
                if not url:
                    continue
                results.append({
                    "title": title,
                    "url": url,
                    "abstract": snippet,
                    "authors": [],
                    "year": None,
                    "citation_count": 0,
                    "source": "google_scholar_web",
                })
            return results

        try:
            return await asyncio.to_thread(_search_sync)
        except Exception:
            # Scholar web fallback should never fail the entire academic search.
            return []

    @staticmethod
    def _dedupe(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for item in results:
            key = (item.get("url") or item.get("title") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        query = tool_input.parameters["query"]
        query_variants_raw = tool_input.parameters.get("query_variants", [])
        sources = tool_input.parameters.get("sources", ["semantic_scholar", "arxiv"])
        queries: list[str] = []
        seen_queries: set[str] = set()
        for candidate in [query, *query_variants_raw]:
            if not isinstance(candidate, str):
                continue
            compact = " ".join(candidate.split()).strip()
            if not compact:
                continue
            lowered = compact.lower()
            if lowered in seen_queries:
                continue
            seen_queries.add(lowered)
            queries.append(compact)

        if not queries:
            queries = [query]

        async def _search() -> list[dict[str, Any]]:
            all_results: list[dict[str, Any]] = []
            for candidate in queries:
                if "semantic_scholar" in sources:
                    all_results.extend(await self._search_semantic_scholar(candidate))
                if "arxiv" in sources:
                    all_results.extend(await self._search_arxiv(candidate))
                if "google_scholar_web" in sources:
                    all_results.extend(await self._search_google_scholar_web(candidate))
                deduped = self._dedupe(all_results)
                if len(deduped) >= self._max_results:
                    return deduped[: self._max_results]
            return self._dedupe(all_results)[: self._max_results]

        try:
            output = await self._circuit_breaker.call(_search)
            return ToolResult(
                tool_name=self.name,
                output=output,
                metadata={"queries_used": queries},
            )
        except Exception as exc:
            return ToolResult(tool_name=self.name, output=None, success=False, error=str(exc))
