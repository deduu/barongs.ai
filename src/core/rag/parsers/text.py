from __future__ import annotations

import asyncio


class TextParser:
    """Parser for plain-text file formats (UTF-8 decode)."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({
            ".txt", ".md", ".csv", ".json", ".log",
            ".py", ".js", ".ts", ".html", ".xml",
        })

    async def parse(self, raw: bytes, filename: str) -> str:
        return await asyncio.to_thread(self._decode, raw)

    def _decode(self, raw: bytes) -> str:
        return raw.decode("utf-8", errors="replace")
