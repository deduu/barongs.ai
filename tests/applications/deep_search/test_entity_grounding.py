from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from src.applications.deep_search.entity_grounding import (
    build_entity_grounding,
    extract_urls,
    fetch_primary_sources,
    strip_urls,
)
from src.core.llm.models import LLMResponse
from src.core.models.results import ToolResult


class TestExtractUrls:
    def test_extracts_single_url(self):
        urls = extract_urls("Research https://github.com/deduu/auditi about AI")
        assert urls == ["https://github.com/deduu/auditi"]

    def test_extracts_multiple_urls(self):
        query = "Compare https://a.com and https://b.com/page"
        urls = extract_urls(query)
        assert urls == ["https://a.com", "https://b.com/page"]

    def test_no_urls_returns_empty(self):
        assert extract_urls("What is Python?") == []

    def test_extracts_url_with_path_and_query_params(self):
        urls = extract_urls("See https://example.com/path?q=1&b=2")
        assert len(urls) == 1
        assert "example.com/path?q=1&b=2" in urls[0]

    def test_handles_parenthesized_url(self):
        urls = extract_urls("about auditi (https://github.com/deduu/auditi) compared")
        assert len(urls) == 1
        assert "github.com/deduu/auditi" in urls[0]


class TestStripUrls:
    def test_removes_urls_from_query(self):
        result = strip_urls("Research https://example.com about AI")
        assert "https://example.com" not in result
        assert "Research" in result
        assert "about AI" in result

    def test_no_urls_returns_original(self):
        assert strip_urls("What is Python?") == "What is Python?"


class TestFetchPrimarySources:
    @pytest.mark.asyncio
    async def test_fetches_urls_with_content_fetcher(self):
        fetcher = AsyncMock()
        fetcher.name = "content_fetcher"
        fetcher.execute = AsyncMock(return_value=ToolResult(
            tool_name="content_fetcher",
            output="This is page content",
        ))

        sources = await fetch_primary_sources(
            ["https://example.com"], fetcher,
        )
        assert len(sources) == 1
        assert sources[0]["url"] == "https://example.com"
        assert sources[0]["content"] == "This is page content"

    @pytest.mark.asyncio
    async def test_limits_to_max_sources(self):
        fetcher = AsyncMock()
        fetcher.name = "content_fetcher"
        fetcher.execute = AsyncMock(return_value=ToolResult(
            tool_name="content_fetcher", output="content",
        ))

        sources = await fetch_primary_sources(
            ["https://a.com", "https://b.com", "https://c.com", "https://d.com"],
            fetcher,
            max_sources=2,
        )
        assert len(sources) == 2

    @pytest.mark.asyncio
    async def test_skips_failed_fetches(self):
        fetcher = AsyncMock()
        fetcher.name = "content_fetcher"
        fetcher.execute = AsyncMock(return_value=ToolResult(
            tool_name="content_fetcher", output=None, success=False, error="timeout",
        ))

        sources = await fetch_primary_sources(["https://fail.com"], fetcher)
        assert sources == []

    @pytest.mark.asyncio
    async def test_truncates_content(self):
        fetcher = AsyncMock()
        fetcher.name = "content_fetcher"
        fetcher.execute = AsyncMock(return_value=ToolResult(
            tool_name="content_fetcher", output="x" * 10000,
        ))

        sources = await fetch_primary_sources(
            ["https://example.com"], fetcher, max_content_per_source=100,
        )
        assert len(sources[0]["content"]) == 100


class TestBuildEntityGrounding:
    @pytest.mark.asyncio
    async def test_builds_grounding_from_sources(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content=json.dumps({
                "name": "Auditi",
                "description": "A Python CLI tool for auditing GitHub repos",
                "key_attributes": ["GitHub audit", "CLI tool", "Python"],
            }),
            model="test",
        ))

        grounding = await build_entity_grounding(
            "What is auditi?",
            [{"url": "https://github.com/deduu/auditi", "content": "Auditi is a CLI..."}],
            llm,
        )
        assert grounding.name == "Auditi"
        assert "audit" in grounding.description.lower()
        assert grounding.source_urls == ["https://github.com/deduu/auditi"]

    @pytest.mark.asyncio
    async def test_builds_grounding_without_urls(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content=json.dumps({
                "name": "Python GIL",
                "description": "Python Global Interpreter Lock",
                "key_attributes": ["concurrency"],
            }),
            model="test",
        ))

        grounding = await build_entity_grounding("How does Python GIL work?", [], llm)
        assert grounding.name == "Python GIL"
        assert grounding.source_urls == []

    @pytest.mark.asyncio
    async def test_handles_malformed_llm_response(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content="I can't parse this into JSON", model="test",
        ))

        grounding = await build_entity_grounding("test query", [], llm)
        # Should fallback gracefully
        assert grounding.name != ""

    @pytest.mark.asyncio
    async def test_handles_markdown_wrapped_json(self):
        inner_json = json.dumps({
            "name": "Auditi",
            "description": "A tool",
            "key_attributes": [],
        })
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content=f"```json\n{inner_json}\n```", model="test",
        ))

        grounding = await build_entity_grounding("test", [], llm)
        assert grounding.name == "Auditi"
