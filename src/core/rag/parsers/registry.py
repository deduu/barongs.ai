from __future__ import annotations

from pathlib import Path
from typing import Any

from src.core.rag.parsers.base import DocumentParser


class ParserRegistry:
    """Routes file extensions to the appropriate DocumentParser."""

    def __init__(self) -> None:
        self._parsers: dict[str, DocumentParser] = {}

    def register(self, parser: DocumentParser) -> None:
        for ext in parser.supported_extensions:
            self._parsers[ext.lower()] = parser

    def get_parser(self, filename: str) -> DocumentParser | None:
        ext = Path(filename).suffix.lower()
        return self._parsers.get(ext)

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset(self._parsers.keys())

    async def parse(self, raw: bytes, filename: str) -> str:
        parser = self.get_parser(filename)
        if parser is None:
            ext = Path(filename).suffix
            supported = sorted(self.supported_extensions)
            raise ValueError(
                f"Unsupported file type: '{ext}'. Supported: {supported}"
            )
        return await parser.parse(raw, filename)


def create_default_registry(
    *,
    llm_provider: Any | None = None,
    vision_model: str = "gpt-4o",
) -> ParserRegistry:
    """Create a registry with all available parsers.

    Parsers with optional dependencies are only registered when
    those dependencies are importable.
    """
    from src.core.rag.parsers.text import TextParser

    registry = ParserRegistry()
    registry.register(TextParser())

    # PDF (optional dependency)
    try:
        from pypdf import PdfReader  # noqa: F401

        from src.core.rag.parsers.pdf import PDFParser

        registry.register(PDFParser())
    except ImportError:
        pass

    # Office (optional dependency)
    try:
        from openpyxl import load_workbook  # noqa: F401
        from pptx import Presentation  # noqa: F401

        from src.core.rag.parsers.office import ExcelParser, PowerPointParser

        registry.register(PowerPointParser())
        registry.register(ExcelParser())
    except ImportError:
        pass

    # Image (requires LLM provider)
    if llm_provider is not None:
        from src.core.rag.parsers.image import ImageParser

        registry.register(ImageParser(
            llm_provider=llm_provider,
            model=vision_model,
        ))

    return registry
