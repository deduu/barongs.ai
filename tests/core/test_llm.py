from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
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


# --- HuggingFace Provider Tests ---

# All HuggingFace tests mock torch + transformers at the module level so they
# run without those heavy dependencies installed.

_HF_MODULE = "src.core.llm.providers.huggingface"


def _make_mock_torch() -> MagicMock:
    """Create a mock torch module with tensor support for tests."""
    mock_torch = MagicMock()

    # Make torch.tensor return a real-ish object with .to(), .shape, slicing
    class FakeTensor:
        def __init__(self, data: list):
            self._data = data
            # Support 2-D tensors [[1,2,3]]
            if isinstance(data[0], list):
                self.shape = (len(data), len(data[0]))
            else:
                self.shape = (len(data),)

        def to(self, device: Any) -> FakeTensor:
            return self

        def __getitem__(self, idx: Any) -> FakeTensor:
            result = self._data[idx]
            if isinstance(result, list):
                return FakeTensor(result)
            return result

        def __len__(self) -> int:
            return self.shape[-1] if len(self.shape) > 1 else self.shape[0]

    def fake_tensor(data: Any) -> FakeTensor:
        return FakeTensor(data)

    mock_torch.tensor = fake_tensor
    mock_torch.no_grad.return_value.__enter__ = MagicMock(return_value=None)
    mock_torch.no_grad.return_value.__exit__ = MagicMock(return_value=False)
    mock_torch.float16 = "float16"
    mock_torch.bfloat16 = "bfloat16"
    mock_torch.float32 = "float32"
    mock_torch.device = MagicMock
    return mock_torch


class TestHuggingFaceProvider:
    """Tests for the HuggingFace local LLM provider."""

    def _make_request(self, system_prompt: str | None = None) -> LLMRequest:
        return LLMRequest(
            messages=[LLMMessage(role="user", content="What is AI?")],
            model="Qwen/Qwen3-4B",
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=256,
        )

    @patch(f"{_HF_MODULE}.torch", new_callable=_make_mock_torch)
    @patch(f"{_HF_MODULE}.AutoModelForCausalLM")
    @patch(f"{_HF_MODULE}.AutoTokenizer")
    def test_name(self, _mock_tok, _mock_model, _mock_torch):
        from src.core.llm.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider

        config = HuggingFaceConfig(quantization="none")
        provider = HuggingFaceProvider(config=config)
        assert provider.name == "huggingface"

    @patch(f"{_HF_MODULE}.torch", new_callable=_make_mock_torch)
    @patch(f"{_HF_MODULE}.AutoModelForCausalLM")
    @patch(f"{_HF_MODULE}.AutoTokenizer")
    def test_build_messages_without_system(self, _mock_tok, _mock_model, _mock_torch):
        from src.core.llm.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider

        config = HuggingFaceConfig(quantization="none")
        provider = HuggingFaceProvider(config=config)
        messages = provider._build_messages(self._make_request())
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "What is AI?"}

    @patch(f"{_HF_MODULE}.torch", new_callable=_make_mock_torch)
    @patch(f"{_HF_MODULE}.AutoModelForCausalLM")
    @patch(f"{_HF_MODULE}.AutoTokenizer")
    def test_build_messages_with_system(self, _mock_tok, _mock_model, _mock_torch):
        from src.core.llm.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider

        config = HuggingFaceConfig(quantization="none")
        provider = HuggingFaceProvider(config=config)
        messages = provider._build_messages(self._make_request(system_prompt="Be concise."))
        assert len(messages) == 2
        assert messages[0] == {"role": "system", "content": "Be concise."}
        assert messages[1] == {"role": "user", "content": "What is AI?"}

    @patch(f"{_HF_MODULE}.torch", new_callable=_make_mock_torch)
    @patch(f"{_HF_MODULE}.AutoModelForCausalLM")
    @patch(f"{_HF_MODULE}.AutoTokenizer")
    async def test_generate_returns_llm_response(
        self, mock_tok_cls, mock_model_cls, mock_torch
    ):
        from src.core.llm.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider

        # Mock tokenizer
        mock_tokenizer = MagicMock()
        input_tensor = mock_torch.tensor([[1, 2, 3]])
        mock_tokenizer.apply_chat_template.return_value = input_tensor
        mock_tokenizer.decode.return_value = "AI is artificial intelligence."
        mock_tok_cls.from_pretrained.return_value = mock_tokenizer

        # Mock model — generate returns prompt + 3 new tokens
        mock_model = MagicMock()
        mock_model.device = "cpu"
        mock_model.generate.return_value = mock_torch.tensor([[1, 2, 3, 4, 5, 6]])
        mock_model_cls.from_pretrained.return_value = mock_model

        config = HuggingFaceConfig(quantization="none")
        provider = HuggingFaceProvider(config=config)
        response = await provider.generate(self._make_request())

        assert isinstance(response, LLMResponse)
        assert response.content == "AI is artificial intelligence."
        assert response.model == "Qwen/Qwen3-4B"
        assert response.finish_reason == "stop"

    @patch(f"{_HF_MODULE}.torch", new_callable=_make_mock_torch)
    @patch(f"{_HF_MODULE}.AutoModelForCausalLM")
    @patch(f"{_HF_MODULE}.AutoTokenizer")
    async def test_generate_usage_stats(self, mock_tok_cls, mock_model_cls, mock_torch):
        from src.core.llm.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider

        mock_tokenizer = MagicMock()
        mock_tokenizer.apply_chat_template.return_value = mock_torch.tensor([[1, 2, 3]])
        mock_tokenizer.decode.return_value = "response"
        mock_tok_cls.from_pretrained.return_value = mock_tokenizer

        mock_model = MagicMock()
        mock_model.device = "cpu"
        # 3 prompt tokens + 4 new tokens = 7 total
        mock_model.generate.return_value = mock_torch.tensor([[1, 2, 3, 10, 11, 12, 13]])
        mock_model_cls.from_pretrained.return_value = mock_model

        config = HuggingFaceConfig(quantization="none")
        provider = HuggingFaceProvider(config=config)
        response = await provider.generate(self._make_request())

        assert response.usage["prompt_tokens"] == 3
        assert response.usage["completion_tokens"] == 4
        assert response.usage["total_tokens"] == 7

    @patch(f"{_HF_MODULE}.asyncio")
    @patch(f"{_HF_MODULE}.torch", new_callable=_make_mock_torch)
    @patch(f"{_HF_MODULE}.AutoModelForCausalLM")
    @patch(f"{_HF_MODULE}.AutoTokenizer")
    async def test_generate_uses_to_thread(
        self, _mock_tok, _mock_model, _mock_torch, mock_asyncio
    ):
        from src.core.llm.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider

        mock_response = LLMResponse(content="ok", model="test")
        mock_asyncio.to_thread = AsyncMock(return_value=mock_response)

        config = HuggingFaceConfig(quantization="none")
        provider = HuggingFaceProvider(config=config)
        await provider.generate(self._make_request())

        mock_asyncio.to_thread.assert_awaited_once()

    @patch(f"{_HF_MODULE}.TextIteratorStreamer")
    @patch(f"{_HF_MODULE}.torch", new_callable=_make_mock_torch)
    @patch(f"{_HF_MODULE}.AutoModelForCausalLM")
    @patch(f"{_HF_MODULE}.AutoTokenizer")
    async def test_stream_yields_tokens(
        self, mock_tok_cls, mock_model_cls, mock_torch, mock_streamer_cls
    ):
        from src.core.llm.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider

        mock_tokenizer = MagicMock()
        mock_tokenizer.apply_chat_template.return_value = mock_torch.tensor([[1, 2, 3]])
        mock_tok_cls.from_pretrained.return_value = mock_tokenizer

        mock_model = MagicMock()
        mock_model.device = "cpu"
        mock_model_cls.from_pretrained.return_value = mock_model

        # Simulate TextIteratorStreamer as a simple iterator
        mock_streamer = MagicMock()
        mock_streamer.__iter__ = MagicMock(return_value=iter(["Hello", " world"]))
        mock_streamer_cls.return_value = mock_streamer

        config = HuggingFaceConfig(quantization="none")
        provider = HuggingFaceProvider(config=config)
        tokens = [token async for token in provider.stream(self._make_request())]

        assert tokens == ["Hello", " world"]

    def test_quantization_config_4bit(self):
        from src.core.llm.providers.huggingface import HuggingFaceConfig

        config = HuggingFaceConfig(quantization="4bit")
        assert config.quantization == "4bit"

    def test_quantization_config_8bit(self):
        from src.core.llm.providers.huggingface import HuggingFaceConfig

        config = HuggingFaceConfig(quantization="8bit")
        assert config.quantization == "8bit"

    def test_quantization_config_none(self):
        from src.core.llm.providers.huggingface import HuggingFaceConfig

        config = HuggingFaceConfig(quantization="none")
        assert config.quantization == "none"

    @patch(f"{_HF_MODULE}.torch", new_callable=_make_mock_torch)
    @patch(f"{_HF_MODULE}.AutoModelForCausalLM")
    @patch(f"{_HF_MODULE}.AutoTokenizer")
    def test_model_loaded_once(self, mock_tok_cls, mock_model_cls, _mock_torch):
        from src.core.llm.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider

        config = HuggingFaceConfig(quantization="none")
        HuggingFaceProvider(config=config)

        mock_model_cls.from_pretrained.assert_called_once()
        mock_tok_cls.from_pretrained.assert_called_once()

    def test_config_defaults(self):
        from src.core.llm.providers.huggingface import HuggingFaceConfig

        config = HuggingFaceConfig()
        assert config.model_id == "Qwen/Qwen3-4B"
        assert config.device_map == "auto"
        assert config.quantization == "4bit"
        assert config.torch_dtype == "float16"
        assert config.max_new_tokens == 2048
        assert config.trust_remote_code is True
