from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMMessage, LLMRequest, LLMResponse
from src.core.llm.providers.openai import OpenAIProvider
from src.core.llm.providers.openai_compatible import OpenAICompatibleProvider
from src.core.llm.registry import LLMProviderRegistry

# --- Stub provider for testing the ABC ---


class StubProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "stub"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content="stub response", model=request.model)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        for token in ["hello", " ", "world"]:
            yield token


# --- ABC Tests ---


class TestLLMProviderABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            LLMProvider()  # type: ignore[abstract]

    async def test_stub_provider_generate(self):
        provider = StubProvider()
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Hi")],
            model="test-model",
        )
        response = await provider.generate(request)
        assert response.content == "stub response"
        assert response.model == "test-model"

    async def test_stub_provider_stream(self):
        provider = StubProvider()
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Hi")],
            model="test-model",
        )
        tokens = [token async for token in provider.stream(request)]
        assert tokens == ["hello", " ", "world"]

    def test_stub_provider_name(self):
        assert StubProvider().name == "stub"


# --- Model Tests ---


class TestLLMModels:
    def test_llm_message_creation(self):
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_llm_request_defaults(self):
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Hi")],
            model="gpt-4o",
        )
        assert request.temperature == 0.7
        assert request.max_tokens == 4096
        assert request.system_prompt is None
        assert request.tools == []

    def test_llm_request_with_system_prompt(self):
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Hi")],
            model="gpt-4o",
            system_prompt="You are helpful.",
        )
        assert request.system_prompt == "You are helpful."

    def test_llm_response_defaults(self):
        response = LLMResponse(content="Hello", model="gpt-4o")
        assert response.usage == {}
        assert response.tool_calls == []
        assert response.finish_reason == "stop"


# --- Registry Tests ---


class TestLLMProviderRegistry:
    def test_register_and_get(self):
        registry = LLMProviderRegistry()
        provider = StubProvider()
        registry.register(provider)
        assert registry.get("stub") is provider

    def test_get_unknown_raises_key_error(self):
        registry = LLMProviderRegistry()
        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")

    def test_list_providers(self):
        registry = LLMProviderRegistry()
        registry.register(StubProvider())
        assert "stub" in registry.list_providers()

    def test_register_overwrites(self):
        registry = LLMProviderRegistry()
        p1 = StubProvider()
        p2 = StubProvider()
        registry.register(p1)
        registry.register(p2)
        assert registry.get("stub") is p2

    def test_empty_registry(self):
        registry = LLMProviderRegistry()
        assert registry.list_providers() == []


# --- OpenAI Provider Tests ---


class TestOpenAIProvider:
    def _make_request(self, system_prompt: str | None = None) -> LLMRequest:
        return LLMRequest(
            messages=[LLMMessage(role="user", content="What is AI?")],
            model="gpt-4o",
            system_prompt=system_prompt,
        )

    def test_name(self):
        provider = OpenAIProvider(api_key="test-key")
        assert provider.name == "openai"

    def test_build_messages_without_system(self):
        provider = OpenAIProvider(api_key="test-key")
        request = self._make_request()
        messages = provider._build_messages(request)
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "What is AI?"}

    def test_build_messages_with_system(self):
        provider = OpenAIProvider(api_key="test-key")
        request = self._make_request(system_prompt="Be concise.")
        messages = provider._build_messages(request)
        assert len(messages) == 2
        assert messages[0] == {"role": "system", "content": "Be concise."}

    @patch("src.core.llm.providers.openai.AsyncOpenAI")
    async def test_generate(self, mock_openai_cls):
        # Set up mock response
        mock_choice = MagicMock()
        mock_choice.message.content = "AI is artificial intelligence."
        mock_choice.message.tool_calls = None
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 5
        mock_usage.total_tokens = 15

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.model = "gpt-4o-2024-08-06"

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key")
        response = await provider.generate(self._make_request())

        assert response.content == "AI is artificial intelligence."
        assert response.model == "gpt-4o-2024-08-06"
        assert response.usage["total_tokens"] == 15
        assert response.finish_reason == "stop"

    @patch("src.core.llm.providers.openai.AsyncOpenAI")
    async def test_generate_with_tool_calls(self, mock_openai_cls):
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "search"
        mock_tool_call.function.arguments = '{"query": "AI"}'

        mock_choice = MagicMock()
        mock_choice.message.content = ""
        mock_choice.message.tool_calls = [mock_tool_call]
        mock_choice.finish_reason = "tool_calls"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = None
        mock_response.model = "gpt-4o"

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key")
        response = await provider.generate(self._make_request())

        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["function"]["name"] == "search"
        assert response.finish_reason == "tool_calls"

    @patch("src.core.llm.providers.openai.AsyncOpenAI")
    async def test_stream(self, mock_openai_cls):
        # Create mock stream chunks
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello"

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " world"

        chunk3 = MagicMock()
        chunk3.choices = []

        async def mock_stream():
            for chunk in [chunk1, chunk2, chunk3]:
                yield chunk

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key")
        tokens = [token async for token in provider.stream(self._make_request())]
        assert tokens == ["Hello", " world"]


# --- OpenAI Compatible Provider Tests ---


class TestOpenAICompatibleProvider:
    def test_name_defaults(self):
        provider = OpenAICompatibleProvider(base_url="http://localhost:8080/v1")
        assert provider.name == "openai_compatible"

    def test_custom_name(self):
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:8080/v1",
            provider_name="vllm_local",
        )
        assert provider.name == "vllm_local"

    def test_api_key_not_required(self):
        provider = OpenAICompatibleProvider(base_url="http://localhost:8080/v1")
        # Should not raise — api_key defaults to "not-needed"
        assert provider.name == "openai_compatible"
