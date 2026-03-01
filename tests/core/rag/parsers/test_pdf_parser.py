from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter
from pypdf.errors import PdfStreamError

from src.core.rag.parsers.pdf import PDFParser


def _make_pdf(text: str = "Hello from PDF") -> bytes:
    """Create a minimal PDF with one page containing the given text."""
    writer = PdfWriter()
    # PdfWriter doesn't have a simple add-text-page, so we build a minimal page
    # using the reportlab-free approach: add a blank page and inject text via annotation
    # Simpler: use pypdf's built-in blank page and accept empty extraction for unit test
    # For a real test, we create a proper PDF stream manually.
    from pypdf._page import PageObject
    from pypdf.generic import NameObject

    page = PageObject.create_blank_page(width=612, height=792)

    # Build a minimal content stream with the text
    content = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET".encode("latin-1")

    from pypdf.generic import DecodedStreamObject, DictionaryObject

    stream = DecodedStreamObject()
    stream.set_data(content)

    # Font dictionary (required for text rendering)
    font_dict = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): font_dict}
            ),
        }
    )
    page[NameObject("/Resources")] = resources
    page[NameObject("/Contents")] = stream

    writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class TestPDFParser:
    def setup_method(self) -> None:
        self.parser = PDFParser()

    def test_supported_extensions(self) -> None:
        assert self.parser.supported_extensions == frozenset({".pdf"})

    @pytest.mark.asyncio
    async def test_parse_pdf_extracts_text(self) -> None:
        pdf_bytes = _make_pdf("Hello from PDF")
        result = await self.parser.parse(pdf_bytes, "test.pdf")
        assert "Hello from PDF" in result

    @pytest.mark.asyncio
    async def test_parse_invalid_pdf_raises(self) -> None:
        with pytest.raises(PdfStreamError):
            await self.parser.parse(b"not a pdf", "bad.pdf")
