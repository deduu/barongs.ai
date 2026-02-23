from __future__ import annotations

from src.core.models.config import AppSettings


class ExampleAppSettings(AppSettings):
    """Settings specific to the example application."""

    app_name: str = "example-app"
    api_key: str = "test-key"
