from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMMessage, LLMRequest

_DESCRIPTION_PROMPT = (
    "Describe this image in detail for a knowledge base. Include all visible text, "
    "data, labels, diagrams, and key visual information. Be thorough and factual."
)

_MIME_MAP: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


class ImageParser:
    """Parser that uses a vision-capable LLM to describe image content."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        model: str = "gpt-4o",
        description_prompt: str = _DESCRIPTION_PROMPT,
    ) -> None:
        self._llm = llm_provider
        self._model = model
        self._prompt = description_prompt

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})

    async def parse(self, raw: bytes, filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        mime_type = _MIME_MAP.get(suffix, "image/png")
        b64 = base64.b64encode(raw).decode("ascii")

        content: list[dict[str, Any]] = [
            {"type": "text", "text": self._prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64}"},
            },
        ]

        request = LLMRequest(
            messages=[LLMMessage(role="user", content=content)],
            model=self._model,
            temperature=0.1,
            max_tokens=1024,
        )
        response = await self._llm.generate(request)
        return response.content
