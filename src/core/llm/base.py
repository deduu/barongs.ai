from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from src.core.llm.models import LLMRequest, LLMResponse


class LLMProvider(ABC):
    """Abstract base class for LLM provider integrations.

    Each provider (OpenAI, Anthropic, local, etc.) implements this interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this provider (e.g. 'openai', 'anthropic')."""
        ...

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Send a request and return the complete response."""
        ...

    @abstractmethod
    def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Send a request and yield response tokens as they arrive."""
        ...
