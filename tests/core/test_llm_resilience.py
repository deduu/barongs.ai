from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.llm.errors import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from src.core.llm.models import LLMMessage, LLMRequest
from src.core.llm.providers.openai import OpenAIProvider
from src.core.middleware.circuit_breaker import CircuitBreakerError


def _make_request() -> LLMRequest:
    return LLMRequest(
        messages=[LLMMessage(role="user", content="Hi")],
        model="gpt-4o",
    )


class TestOpenAIProviderErrorTranslation:
    """Verify that OpenAI SDK exceptions are translated to LLMProviderError subtypes."""

    @patch("src.core.llm.providers.openai.AsyncOpenAI")
    async def test_auth_error_translated(self, mock_openai_cls):
        from openai import AuthenticationError

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.headers = {}
        mock_client.chat.completions.create = AsyncMock(
            side_effect=AuthenticationError(
                message="Invalid API key",
                response=mock_resp,
                body=None,
            )
        )
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="bad-key")
        with pytest.raises(LLMAuthenticationError) as exc_info:
            await provider.generate(_make_request())
        assert exc_info.value.provider == "openai"

    @patch("src.core.llm.providers.openai.AsyncOpenAI")
    async def test_rate_limit_error_translated(self, mock_openai_cls):
        from openai import RateLimitError

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"retry-after": "5"}
        mock_client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                message="Rate limit exceeded",
                response=mock_resp,
                body=None,
            )
        )
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key")
        with pytest.raises(LLMRateLimitError) as exc_info:
            await provider.generate(_make_request())
        assert exc_info.value.retry_after == 5.0

    @patch("src.core.llm.providers.openai.AsyncOpenAI")
    async def test_timeout_error_translated(self, mock_openai_cls):
        from openai import APITimeoutError

        mock_client = AsyncMock()
        mock_req = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError(request=mock_req)
        )
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key")
        with pytest.raises(LLMTimeoutError) as exc_info:
            await provider.generate(_make_request())
        assert exc_info.value.provider == "openai"

    @patch("src.core.llm.providers.openai.AsyncOpenAI")
    async def test_generic_api_error_translated(self, mock_openai_cls):
        from openai import APIStatusError

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.headers = {}
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APIStatusError(
                message="Internal error",
                response=mock_resp,
                body=None,
            )
        )
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key")
        with pytest.raises(LLMProviderError) as exc_info:
            await provider.generate(_make_request())
        assert exc_info.value.status_code == 500
        assert exc_info.value.retryable is True  # 5xx are retryable

    @patch("src.core.llm.providers.openai.AsyncOpenAI")
    async def test_stream_auth_error_translated(self, mock_openai_cls):
        from openai import AuthenticationError

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.headers = {}
        mock_client.chat.completions.create = AsyncMock(
            side_effect=AuthenticationError(
                message="Invalid API key",
                response=mock_resp,
                body=None,
            )
        )
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="bad-key")
        with pytest.raises(LLMAuthenticationError):
            async for _ in provider.stream(_make_request()):
                pass


class TestOpenAIProviderCircuitBreaker:
    """Verify circuit breaker integration in the OpenAI provider."""

    @patch("src.core.llm.providers.openai.AsyncOpenAI")
    async def test_circuit_opens_after_repeated_failures(self, mock_openai_cls):
        from openai import APIStatusError

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.headers = {}
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APIStatusError(
                message="Server error",
                response=mock_resp,
                body=None,
            )
        )
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key", circuit_breaker_threshold=3)
        req = _make_request()

        # First 3 calls fail with LLMProviderError (circuit still trying)
        for _ in range(3):
            with pytest.raises(LLMProviderError):
                await provider.generate(req)

        # 4th call should trip the circuit breaker
        with pytest.raises(CircuitBreakerError):
            await provider.generate(req)

    @patch("src.core.llm.providers.openai.AsyncOpenAI")
    async def test_circuit_resets_on_success(self, mock_openai_cls):
        from openai import APIStatusError

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.headers = {}

        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise APIStatusError(
                    message="Server error", response=mock_resp, body=None
                )
            # Return success
            mock_choice = MagicMock()
            mock_choice.message.content = "ok"
            mock_choice.message.tool_calls = None
            mock_choice.finish_reason = "stop"
            mock_success = MagicMock()
            mock_success.choices = [mock_choice]
            mock_success.usage = None
            mock_success.model = "gpt-4o"
            return mock_success

        mock_client.chat.completions.create = AsyncMock(side_effect=side_effect)
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key", circuit_breaker_threshold=3)
        req = _make_request()

        # 2 failures
        for _ in range(2):
            with pytest.raises(LLMProviderError):
                await provider.generate(req)

        # Success resets the circuit
        response = await provider.generate(req)
        assert response.content == "ok"

    @patch("src.core.llm.providers.openai.AsyncOpenAI")
    async def test_auth_errors_do_not_trip_circuit(self, mock_openai_cls):
        """Auth errors are permanent — they should NOT count toward circuit breaker."""
        from openai import AuthenticationError

        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.headers = {}
        mock_client.chat.completions.create = AsyncMock(
            side_effect=AuthenticationError(
                message="Invalid key", response=mock_resp, body=None
            )
        )
        mock_openai_cls.return_value = mock_client

        provider = OpenAIProvider(api_key="bad-key", circuit_breaker_threshold=2)
        req = _make_request()

        # Even after many auth failures, circuit stays closed (raises auth error, not circuit error)
        for _ in range(5):
            with pytest.raises(LLMAuthenticationError):
                await provider.generate(req)
