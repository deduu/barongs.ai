from __future__ import annotations

from pydantic import BaseModel, Field


class Source(BaseModel):
    """A single search result source with extracted content."""

    url: str
    title: str
    snippet: str = ""
    content: str = ""  # Extracted full text
    index: int = 0  # Citation number [1], [2], etc.


class SearchQuery(BaseModel):
    """Analyzed query with classification and refined search terms."""

    original: str
    refined_queries: list[str] = Field(default_factory=list)
    query_type: str = "search"  # "search" | "direct"


class SearchResult(BaseModel):
    """Complete search result with synthesized response and sources."""

    sources: list[Source] = Field(default_factory=list)
    response: str = ""
    query: SearchQuery
