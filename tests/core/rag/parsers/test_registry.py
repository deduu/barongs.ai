from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.core.rag.parsers.registry import ParserRegistry, create_default_registry
from src.core.rag.parsers.text import TextParser


class TestParserRegistry:
    def setup_method(self) -> None:
        self.registry = ParserRegistry()
        self.registry.register(TextParser())

    def test_get_parser_by_extension(self) -> None:
        parser = self.registry.get_parser("readme.txt")
        assert parser is not None
        assert ".txt" in parser.supported_extensions

    def test_get_parser_returns_none_for_unknown(self) -> None:
        parser = self.registry.get_parser("file.mp4")
        assert parser is None

    def test_case_insensitive_extension(self) -> None:
        parser = self.registry.get_parser("FILE.TXT")
        # Extensions are registered lowercase; uppercase should still match
        # because get_parser lowercases the input
        assert parser is not None

    def test_supported_extensions(self) -> None:
        exts = self.registry.supported_extensions
        assert ".txt" in exts
        assert ".md" in exts

    @pytest.mark.asyncio
    async def test_parse_routes_correctly(self) -> None:
        result = await self.registry.parse(b"hello", "test.txt")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_parse_unsupported_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported file type"):
            await self.registry.parse(b"data", "file.mp4")


class TestCreateDefaultRegistry:
    def test_always_has_text_parser(self) -> None:
        registry = create_default_registry()
        assert ".txt" in registry.supported_extensions

    def test_has_pdf_support(self) -> None:
        registry = create_default_registry()
        assert ".pdf" in registry.supported_extensions

    def test_has_office_support(self) -> None:
        registry = create_default_registry()
        assert ".pptx" in registry.supported_extensions
        assert ".xlsx" in registry.supported_extensions

    def test_no_image_without_llm(self) -> None:
        registry = create_default_registry()
        assert ".png" not in registry.supported_extensions

    def test_image_with_llm(self) -> None:
        mock_llm = AsyncMock()
        registry = create_default_registry(llm_provider=mock_llm)
        assert ".png" in registry.supported_extensions
        assert ".jpg" in registry.supported_extensions
