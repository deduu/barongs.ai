from __future__ import annotations

from src.core.llm.providers.openai import OpenAIProvider


class OpenAICompatibleProvider(OpenAIProvider):
    """LLM provider for OpenAI-compatible APIs (vLLM, SGLang, Ollama, LM Studio).

    Uses the same OpenAI SDK with a custom base_url pointing to the local/remote
    inference server.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str = "not-needed",
        default_model: str = "default",
        provider_name: str = "openai_compatible",
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url, default_model=default_model)
        self._provider_name = provider_name

    @property
    def name(self) -> str:
        return self._provider_name
