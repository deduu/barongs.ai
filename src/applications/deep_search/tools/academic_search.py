from __future__ import annotations

from typing import Any
from xml.etree import ElementTree

from src.core.http.client import HttpClientPool
from src.core.interfaces.tool import Tool
from src.core.middleware.circuit_breaker import CircuitBreaker
from src.core.models.context import ToolInput
from src.core.models.results import ToolResult

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_URL = "http://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


class AcademicSearchTool(Tool):
    """Search academic papers via Semantic Scholar and arXiv APIs."""

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
        return "Search academic papers from Semantic Scholar and arXiv."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Academic search query"},
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Sources to query: 'semantic_scholar', 'arxiv'. Default: both.",
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

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        query = tool_input.parameters["query"]
        sources = tool_input.parameters.get("sources", ["semantic_scholar", "arxiv"])

        async def _search() -> list[dict[str, Any]]:
            all_results: list[dict[str, Any]] = []
            if "semantic_scholar" in sources:
                all_results.extend(await self._search_semantic_scholar(query))
            if "arxiv" in sources:
                all_results.extend(await self._search_arxiv(query))
            return all_results

        try:
            output = await self._circuit_breaker.call(_search)
            return ToolResult(tool_name=self.name, output=output)
        except Exception as exc:
            return ToolResult(tool_name=self.name, output=None, success=False, error=str(exc))
