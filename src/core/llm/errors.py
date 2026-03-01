from __future__ import annotations


class LLMProviderError(Exception):
    """Base error for all LLM provider failures."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        self.provider = provider
        self.status_code = status_code
        self.retryable = retryable
        super().__init__(f"[{provider}] {message}")


class LLMAuthenticationError(LLMProviderError):
    """Raised when the LLM provider rejects authentication credentials."""

    def __init__(self, *, provider: str, message: str = "Authentication failed") -> None:
        super().__init__(message, provider=provider, status_code=401, retryable=False)


class LLMRateLimitError(LLMProviderError):
    """Raised when the LLM provider returns a rate-limit response."""

    def __init__(
        self,
        *,
        provider: str,
        retry_after: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        msg = "Rate limit exceeded"
        if retry_after is not None:
            msg += f" (retry after {retry_after}s)"
        super().__init__(msg, provider=provider, status_code=429, retryable=True)


class LLMTimeoutError(LLMProviderError):
    """Raised when an LLM call exceeds its timeout."""

    def __init__(self, *, provider: str, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Request timed out after {timeout_seconds}s",
            provider=provider,
            retryable=True,
        )
