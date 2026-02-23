from __future__ import annotations

from src.core.llm.providers.openai import OpenAIProvider
from src.core.llm.providers.openai_compatible import OpenAICompatibleProvider

__all__ = [
    "OpenAICompatibleProvider",
    "OpenAIProvider",
]

# HuggingFace provider is optional (requires torch + transformers).
try:
    from src.core.llm.providers.huggingface import HuggingFaceProvider  # noqa: F401

    __all__.append("HuggingFaceProvider")
except ImportError:
    pass
