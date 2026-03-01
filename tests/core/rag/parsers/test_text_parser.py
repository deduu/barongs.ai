from __future__ import annotations

import pytest

from src.core.rag.parsers.text import TextParser


class TestTextParser:
    def setup_method(self) -> None:
        self.parser = TextParser()

    def test_supported_extensions(self) -> None:
        exts = self.parser.supported_extensions
        assert ".txt" in exts
        assert ".md" in exts
        assert ".csv" in exts
        assert ".json" in exts
        assert ".py" in exts
        assert ".html" in exts
        assert ".xml" in exts

    @pytest.mark.asyncio
    async def test_parse_utf8(self) -> None:
        raw = b"Hello, world!"
        result = await self.parser.parse(raw, "test.txt")
        assert result == "Hello, world!"

    @pytest.mark.asyncio
    async def test_parse_with_replacement(self) -> None:
        raw = b"Hello \xff\xfe world"
        result = await self.parser.parse(raw, "test.txt")
        assert "Hello" in result
        assert "world" in result

    @pytest.mark.asyncio
    async def test_parse_empty(self) -> None:
        result = await self.parser.parse(b"", "empty.txt")
        assert result == ""
