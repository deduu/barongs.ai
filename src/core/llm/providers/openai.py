from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
from openai import AsyncOpenAI

from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMRequest, LLMResponse


class OpenAIProvider(LLMProvider):
    """LLM provider for the OpenAI API (GPT-4o, etc.)."""

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        default_model: str = "gpt-4o",
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=httpx.Timeout(30.0, connect=5.0),
        )
        self._default_model = default_model

    @property
    def name(self) -> str:
        return "openai"

    def _build_messages(self, request: LLMRequest) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})
        return messages

    def _build_kwargs(self, request: LLMRequest) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": request.model or self._default_model,
            "messages": self._build_messages(request),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.tools:
            kwargs["tools"] = request.tools
        return kwargs

    async def generate(self, request: LLMRequest) -> LLMResponse:
        kwargs = self._build_kwargs(request)
        response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        content = choice.message.content or ""

        tool_calls: list[dict[str, Any]] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                )

        usage: dict[str, int] = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            content=content,
            model=response.model,
            usage=usage,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        kwargs = self._build_kwargs(request)
        kwargs["stream"] = True
        response = await self._client.chat.completions.create(**kwargs)

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
