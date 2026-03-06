from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.applications.deep_search.query_utils import normalize_research_query
from src.applications.deep_search.models.research import EntityGrounding
from src.core.interfaces.tool import Tool
from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMMessage, LLMRequest
from src.core.models.context import ToolInput

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"https?://[^\s<>\"'\)\]]+", re.IGNORECASE)

_GROUNDING_SYSTEM_PROMPT = (
    "Extract the identity of the specific entity the user is asking about. "
    "Return ONLY valid JSON:\n"
    '{"name": "...", "description": "2-3 sentence disambiguating description", '
    '"key_attributes": ["attribute1", "attribute2"]}\n\n'
    "Be as specific as possible to avoid confusing this entity with others "
    "that share the same name. "
    "If the query is ambiguous and no primary sources are provided, do NOT guess the domain. "
    "Use a generic description that explicitly says the entity is ambiguous from the provided context."
)

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")


def _query_tokens(query: str) -> list[str]:
    return [token.lower() for token in _TOKEN_PATTERN.findall(normalize_research_query(query))]


def _likely_ambiguous_name(name: str) -> bool:
    tokens = _TOKEN_PATTERN.findall(name)
    return len(tokens) == 1


def _generic_grounding(name: str, query: str) -> dict[str, Any]:
    query_tokens = [token for token in _query_tokens(query) if token.lower() != name.lower()]
    return {
        "name": name,
        "description": (
            f"Entity named {name} referenced in the user query. "
            "Its domain is ambiguous from the provided context, so it should not be grounded "
            "to a specific product category without supporting sources."
        ),
        "key_attributes": query_tokens[:4],
        "needs_disambiguation": True,
        "clarification_prompt": (
            f"The name '{name}' is ambiguous from your query alone. "
            "Clarify which specific product, company, or system you mean before research continues."
        ),
    }


def grounding_requires_disambiguation(data: dict[str, Any]) -> bool:
    """Return True when the grounding is too ambiguous to research safely."""
    if bool(data.get("needs_disambiguation")):
        return True
    description = str(data.get("description", "")).lower()
    return "ambiguous from the provided context" in description


def _should_genericize_grounding(
    *,
    query: str,
    primary_sources: list[dict[str, Any]],
    data: dict[str, Any],
) -> bool:
    if primary_sources:
        return False
    name = str(data.get("name", "")).strip()
    description = str(data.get("description", "")).strip()
    if not name or not description or not _likely_ambiguous_name(name):
        return False
    query_terms = set(_query_tokens(query))
    if name.lower() in query_terms:
        query_terms.remove(name.lower())
    description_terms = {
        token.lower()
        for token in _TOKEN_PATTERN.findall(description)
        if len(token) >= 4 and token.lower() != name.lower()
    }
    return bool(description_terms) and description_terms.isdisjoint(query_terms)


def extract_urls(query: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from the user's query string."""
    return _URL_PATTERN.findall(query)


def strip_urls(query: str) -> str:
    """Return the query with URLs removed."""
    return _URL_PATTERN.sub("", query).strip()


async def fetch_primary_sources(
    urls: list[str],
    content_fetcher: Tool,
    *,
    max_sources: int = 3,
    max_content_per_source: int = 4000,
) -> list[dict[str, Any]]:
    """Fetch content from user-provided URLs using ContentFetcherTool."""
    sources: list[dict[str, Any]] = []
    for url in urls[:max_sources]:
        result = await content_fetcher.execute(
            ToolInput(tool_name=content_fetcher.name, parameters={"url": url})
        )
        if result.success and result.output:
            content = (
                result.output[:max_content_per_source]
                if isinstance(result.output, str)
                else str(result.output)[:max_content_per_source]
            )
            sources.append({"url": url, "content": content})
    return sources


async def build_entity_grounding(
    query: str,
    primary_sources: list[dict[str, Any]],
    llm: LLMProvider,
    model: str = "gpt-4o",
) -> EntityGrounding:
    """Use an LLM call to extract structured entity identity from the query + primary sources."""
    source_text = ""
    source_urls: list[str] = []
    for src in primary_sources:
        source_text += f"\n\nURL: {src['url']}\nContent: {src['content'][:3000]}"
        source_urls.append(src["url"])

    request = LLMRequest(
        messages=[
            LLMMessage(
                role="user",
                content=(
                    f"User query: {query}\n\n"
                    f"Primary source content:{source_text if source_text else ' (no URLs provided)'}"
                ),
            )
        ],
        model=model,
        system_prompt=_GROUNDING_SYSTEM_PROMPT,
        temperature=0.1,
        max_tokens=300,
    )
    response = await llm.generate(request)

    try:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response.content)
        raw = match.group(1) if match else response.content
        data: dict[str, Any] = json.loads(raw.strip())
    except (ValueError, AttributeError):
        logger.debug("Failed to parse entity grounding JSON, using fallback")
        clean_query = strip_urls(query)
        data = {
            "name": clean_query[:100],
            "description": clean_query,
            "key_attributes": [],
        }

    if _should_genericize_grounding(
        query=query,
        primary_sources=primary_sources,
        data=data,
    ):
        data = _generic_grounding(str(data.get("name", "")).strip(), query)

    return EntityGrounding(
        name=data.get("name", ""),
        description=data.get("description", ""),
        key_attributes=data.get("key_attributes", []),
        source_urls=source_urls,
        primary_source_content=source_text[:5000],
        needs_disambiguation=bool(data.get("needs_disambiguation", False)),
        clarification_prompt=str(data.get("clarification_prompt", "")),
    )
