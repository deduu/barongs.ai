from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DocumentParser(Protocol):
    """Protocol for converting raw file bytes into plain text."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        """File extensions this parser handles (e.g., frozenset({'.pdf'}))."""
        ...

    async def parse(self, raw: bytes, filename: str) -> str:
        """Extract text content from raw file bytes.

        Args:
            raw: The raw bytes of the uploaded file.
            filename: Original filename (used for extension detection).

        Returns:
            Extracted text content as a string.

        Raises:
            ValueError: If the file cannot be parsed.
        """
        ...
