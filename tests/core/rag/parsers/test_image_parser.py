from __future__ import annotations

import base64
from unittest.mock import AsyncMock

import pytest

from src.core.llm.models import LLMResponse
from src.core.rag.parsers.image import ImageParser


def _make_tiny_png() -> bytes:
    """Create a minimal valid 1x1 PNG (67 bytes)."""
    import struct
    import zlib

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw_data = b"\x00\x00\x00\x00"  # filter byte + 1 RGB pixel
    idat = zlib.compress(raw_data)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


class TestImageParser:
    def setup_method(self) -> None:
        self.mock_llm = AsyncMock()
        self.mock_llm.generate = AsyncMock(
            return_value=LLMResponse(
                content="A small red square on a white background.",
                model="gpt-4o",
                usage={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
            )
        )
        self.parser = ImageParser(llm_provider=self.mock_llm, model="gpt-4o")

    def test_supported_extensions(self) -> None:
        exts = self.parser.supported_extensions
        assert ".png" in exts
        assert ".jpg" in exts
        assert ".jpeg" in exts
        assert ".webp" in exts

    @pytest.mark.asyncio
    async def test_parse_sends_multimodal_request(self) -> None:
        png_bytes = _make_tiny_png()
        result = await self.parser.parse(png_bytes, "photo.png")

        assert result == "A small red square on a white background."

        # Verify the LLM was called with multimodal content
        call_args = self.mock_llm.generate.call_args
        request = call_args[0][0]
        assert len(request.messages) == 1

        msg = request.messages[0]
        assert msg.role == "user"
        assert isinstance(msg.content, list)
        assert len(msg.content) == 2
        assert msg.content[0]["type"] == "text"
        assert msg.content[1]["type"] == "image_url"

        # Verify base64 encoding is correct
        b64_in_url = msg.content[1]["image_url"]["url"]
        assert b64_in_url.startswith("data:image/png;base64,")
        encoded_data = b64_in_url.split(",", 1)[1]
        assert base64.b64decode(encoded_data) == png_bytes

    @pytest.mark.asyncio
    async def test_parse_jpeg_uses_correct_mime(self) -> None:
        png_bytes = _make_tiny_png()  # content doesn't matter for mime detection
        await self.parser.parse(png_bytes, "photo.jpg")

        call_args = self.mock_llm.generate.call_args
        request = call_args[0][0]
        url = request.messages[0].content[1]["image_url"]["url"]
        assert url.startswith("data:image/jpeg;base64,")
