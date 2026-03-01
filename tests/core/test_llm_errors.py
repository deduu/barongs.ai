from __future__ import annotations

from src.core.llm.errors import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)


class TestLLMProviderError:
    def test_basic_creation(self):
        err = LLMProviderError("something broke", provider="openai")
        assert str(err) == "[openai] something broke"
        assert err.provider == "openai"
        assert err.status_code is None
        assert err.retryable is False

    def test_with_status_code(self):
        err = LLMProviderError("bad request", provider="openai", status_code=400)
        assert err.status_code == 400

    def test_retryable_flag(self):
        err = LLMProviderError("transient", provider="openai", retryable=True)
        assert err.retryable is True

    def test_is_exception(self):
        assert issubclass(LLMProviderError, Exception)


class TestLLMAuthenticationError:
    def test_creation(self):
        err = LLMAuthenticationError(provider="openai")
        assert err.provider == "openai"
        assert err.status_code == 401
        assert err.retryable is False
        assert "authentication" in str(err).lower()

    def test_custom_message(self):
        err = LLMAuthenticationError(provider="openai", message="Invalid key")
        assert "Invalid key" in str(err)


class TestLLMRateLimitError:
    def test_creation(self):
        err = LLMRateLimitError(provider="openai")
        assert err.provider == "openai"
        assert err.status_code == 429
        assert err.retryable is True
        assert err.retry_after is None

    def test_with_retry_after(self):
        err = LLMRateLimitError(provider="openai", retry_after=30.0)
        assert err.retry_after == 30.0


class TestLLMTimeoutError:
    def test_creation(self):
        err = LLMTimeoutError(provider="openai", timeout_seconds=30.0)
        assert err.provider == "openai"
        assert err.retryable is True
        assert err.timeout_seconds == 30.0
        assert "30.0" in str(err)
