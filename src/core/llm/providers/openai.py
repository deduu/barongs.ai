from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from typing import Any

import httpx
from openai import (
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from src.core.llm.base import LLMProvider
from src.core.llm.errors import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from src.core.llm.models import LLMRequest, LLMResponse
from src.core.middleware.circuit_breaker import CircuitBreaker


class OpenAIProvider(LLMProvider):
    """LLM provider for the OpenAI API (GPT-4o, etc.)."""

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        default_model: str = "gpt-4o",
        circuit_breaker_threshold: int = 5,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=httpx.Timeout(30.0, connect=5.0),
        )
        self._default_model = default_model
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=30.0,
            expected_exceptions=(LLMProviderError,),
            should_count=lambda exc: getattr(exc, "retryable", False),
        )

    @property
    def name(self) -> str:
        return "openai"

    def _build_messages(self, request: LLMRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
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

    def _translate_error(self, exc: Exception) -> LLMProviderError:
        """Translate OpenAI SDK exceptions into our error hierarchy."""
        if isinstance(exc, AuthenticationError):
            raise LLMAuthenticationError(provider=self.name) from exc
        if isinstance(exc, RateLimitError):
            retry_after: float | None = None
            raw = getattr(exc, "response", None)
            if raw is not None:
                val = raw.headers.get("retry-after")
                if val is not None:
                    with contextlib.suppress(ValueError, TypeError):
                        retry_after = float(val)
            raise LLMRateLimitError(provider=self.name, retry_after=retry_after) from exc
        if isinstance(exc, APITimeoutError):
            raise LLMTimeoutError(provider=self.name, timeout_seconds=30.0) from exc
        if isinstance(exc, APIStatusError):
            code = exc.response.status_code
            raise LLMProviderError(
                str(exc),
                provider=self.name,
                status_code=code,
                retryable=code >= 500,
            ) from exc
        raise LLMProviderError(
            str(exc), provider=self.name, retryable=False
        ) from exc

    async def generate(self, request: LLMRequest) -> LLMResponse:
        async def _call() -> LLMResponse:
            try:
                kwargs = self._build_kwargs(request)
                response = await self._client.chat.completions.create(**kwargs)
            except AuthenticationError as exc:
                # Auth errors are permanent — bypass circuit breaker
                raise LLMAuthenticationError(provider=self.name) from exc
            except (RateLimitError, APITimeoutError, APIStatusError) as exc:
                self._translate_error(exc)
            except LLMProviderError:
                raise
            except Exception as exc:
                self._translate_error(exc)

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

        return await self._circuit_breaker.call(_call)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        try:
            kwargs = self._build_kwargs(request)
            kwargs["stream"] = True
            response = await self._client.chat.completions.create(**kwargs)
        except (AuthenticationError, RateLimitError, APITimeoutError, APIStatusError) as exc:
            self._translate_error(exc)
        except Exception as exc:
            self._translate_error(exc)

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
