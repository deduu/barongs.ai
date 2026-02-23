from __future__ import annotations

from src.core.llm.base import LLMProvider


class LLMProviderRegistry:
    """Registry for managing multiple LLM providers by name."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        """Register a provider. Overwrites if name already exists."""
        self._providers[provider.name] = provider

    def get(self, name: str) -> LLMProvider:
        """Get a provider by name. Raises KeyError if not found."""
        if name not in self._providers:
            available = ", ".join(self._providers) or "(none)"
            raise KeyError(f"LLM provider '{name}' not found. Available: {available}")
        return self._providers[name]

    def list_providers(self) -> list[str]:
        """Return names of all registered providers."""
        return list(self._providers)
