from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from src.core.llm.models import LLMMessage, LLMRequest


class TestLLMMessageMultimodal:
    def test_str_content_still_works(self) -> None:
        msg = LLMMessage(role="user", content="Hello")
        assert msg.content == "Hello"

    def test_list_content_for_vision(self) -> None:
        content: list[dict[str, Any]] = [
            {"type": "text", "text": "Describe this image"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
        ]
        msg = LLMMessage(role="user", content=content)
        assert isinstance(msg.content, list)
        assert len(msg.content) == 2
        assert msg.content[0]["type"] == "text"
        assert msg.content[1]["type"] == "image_url"


class TestOpenAIProviderMultimodal:
    @pytest.mark.asyncio
    async def test_build_messages_passes_list_content(self) -> None:
        from src.core.llm.providers.openai import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key")
        content: list[dict[str, Any]] = [
            {"type": "text", "text": "Describe this"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
        ]
        request = LLMRequest(
            messages=[LLMMessage(role="user", content=content)],
            model="gpt-4o",
        )
        messages = provider._build_messages(request)
        # The user message should have the list content passed through
        user_msg = messages[-1]
        assert user_msg["role"] == "user"
        assert isinstance(user_msg["content"], list)
        assert user_msg["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_build_messages_still_works_with_str(self) -> None:
        from src.core.llm.providers.openai import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key")
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Hello")],
            model="gpt-4o",
        )
        messages = provider._build_messages(request)
        user_msg = messages[-1]
        assert user_msg["content"] == "Hello"


class TestHuggingFaceProviderMultimodal:
    @pytest.mark.asyncio
    async def test_rejects_multimodal_content(self) -> None:
        from src.core.llm.errors import LLMProviderError

        # Import with lazy-load guard since torch may not be installed
        try:
            from src.core.llm.providers.huggingface import HuggingFaceConfig, HuggingFaceProvider
        except ImportError:
            pytest.skip("HuggingFace dependencies not installed")

        # We need to mock the model loading since we don't have torch
        with patch("src.core.llm.providers.huggingface.AutoModelForCausalLM"), \
             patch("src.core.llm.providers.huggingface.AutoTokenizer"):
            config = HuggingFaceConfig(model_id="test-model")
            provider = HuggingFaceProvider(config=config)

        content: list[dict[str, Any]] = [
            {"type": "text", "text": "Describe this"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
        ]
        request = LLMRequest(
            messages=[LLMMessage(role="user", content=content)],
            model="test-model",
        )
        with pytest.raises(LLMProviderError, match="multimodal"):
            provider._build_messages(request)
