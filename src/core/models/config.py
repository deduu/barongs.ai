from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Base configuration loaded from environment / .env file.

    Every application extends this with its own settings.
    All env vars are prefixed with PROM_ to avoid collisions.
    """

    # General
    app_name: str = "pormetheus"
    debug: bool = False
    log_level: str = "INFO"
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Security
    api_key: str = Field(default="changeme", description="API key for auth")
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    openai_auth_enabled: bool = False

    # Timeouts
    agent_timeout_seconds: float = 30.0
    tool_timeout_seconds: float = 15.0

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Circuit breaker
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 30

    model_config = {
        "env_prefix": "PROM_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }
