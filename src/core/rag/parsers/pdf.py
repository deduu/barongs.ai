from __future__ import annotations

import asyncio
import io

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None  # type: ignore[assignment,misc]

_INSTALL_MSG = "PDF parsing requires pypdf. Install with: pip install barongsai[rag-parsers]"


class PDFParser:
    """Parser for PDF documents using pypdf."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".pdf"})

    async def parse(self, raw: bytes, filename: str) -> str:
        if PdfReader is None:
            raise ImportError(_INSTALL_MSG)
        return await asyncio.to_thread(self._extract, raw)

    def _extract(self, raw: bytes) -> str:
        reader = PdfReader(io.BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
