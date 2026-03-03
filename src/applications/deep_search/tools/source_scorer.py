from __future__ import annotations

import datetime
from typing import Any
from urllib.parse import urlparse

from src.core.interfaces.tool import Tool
from src.core.models.context import ToolInput
from src.core.models.results import ToolResult

# Domain authority tiers
_GOV_EDU_DOMAINS = (".gov", ".edu", ".ac.uk", ".edu.au")
_HIGH_TRUST_DOMAINS = (
    "reuters.com", "apnews.com", "bbc.com", "nature.com",
    "science.org", "thelancet.com", "nejm.org", "ieee.org",
    "acm.org", "springer.com", "wiley.com",
)
_MEDIUM_TRUST_DOMAINS = (
    "nytimes.com", "washingtonpost.com", "theguardian.com",
    "wired.com", "arstechnica.com", "techcrunch.com",
)
_LOW_TRUST_INDICATORS = (
    "wordpress.com", "blogspot.com", "medium.com", "substack.com",
    "reddit.com", "quora.com",
)


class SourceScorerTool(Tool):
    """Score source credibility based on domain, recency, citations, and peer review."""

    @property
    def name(self) -> str:
        return "source_scorer"

    @property
    def description(self) -> str:
        return "Score the credibility of a source based on domain authority, recency, and citations."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL of the source"},
                "year": {"type": "integer", "description": "Publication year (optional)"},
                "citation_count": {"type": "integer", "description": "Number of citations"},
                "is_peer_reviewed": {"type": "boolean", "description": "Whether peer-reviewed"},
            },
            "required": ["url"],
        }

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        url = tool_input.parameters["url"]
        year = tool_input.parameters.get("year")
        citation_count = tool_input.parameters.get("citation_count", 0)
        is_peer_reviewed = tool_input.parameters.get("is_peer_reviewed", False)

        domain_authority = self._score_domain(url)
        recency_score = self._score_recency(year)
        citation_score = self._score_citations(citation_count)

        # Weighted overall score
        overall = (
            domain_authority * 0.35
            + recency_score * 0.20
            + citation_score * 0.20
            + (0.25 if is_peer_reviewed else 0.0)
        )
        overall = min(1.0, max(0.0, overall))

        return ToolResult(
            tool_name=self.name,
            output={
                "domain_authority": round(domain_authority, 3),
                "recency_score": round(recency_score, 3),
                "citation_count": citation_count,
                "is_peer_reviewed": is_peer_reviewed,
                "overall_score": round(overall, 3),
            },
        )

    @staticmethod
    def _score_domain(url: str) -> float:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        # Check .gov / .edu TLDs
        for suffix in _GOV_EDU_DOMAINS:
            if hostname.endswith(suffix):
                return 0.9

        # High-trust news/academic publishers
        for domain in _HIGH_TRUST_DOMAINS:
            if domain in hostname:
                return 0.8

        # Medium-trust established outlets
        for domain in _MEDIUM_TRUST_DOMAINS:
            if domain in hostname:
                return 0.65

        # Low-trust blog platforms
        for indicator in _LOW_TRUST_INDICATORS:
            if indicator in hostname:
                return 0.3

        # Default for unknown domains
        return 0.5

    @staticmethod
    def _score_recency(year: int | None) -> float:
        if year is None:
            return 0.5
        current_year = datetime.datetime.now(tz=datetime.UTC).year
        age = current_year - year
        if age <= 0:
            return 1.0
        if age <= 1:
            return 0.9
        if age <= 3:
            return 0.7
        if age <= 5:
            return 0.5
        if age <= 10:
            return 0.3
        return 0.1

    @staticmethod
    def _score_citations(count: int) -> float:
        if count <= 0:
            return 0.1
        if count < 10:
            return 0.3
        if count < 50:
            return 0.5
        if count < 200:
            return 0.7
        if count < 1000:
            return 0.85
        return 1.0
