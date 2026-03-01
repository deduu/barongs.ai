from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.models.config import AppSettings


class TestProductionConfigValidation:
    def test_production_rejects_default_api_key(self):
        with pytest.raises(ValidationError, match="api_key"):
            AppSettings(
                environment="production",
                api_key="changeme",
            )

    def test_production_rejects_wildcard_cors(self):
        with pytest.raises(ValidationError, match="cors_origins"):
            AppSettings(
                environment="production",
                api_key="real-secret-key",
                cors_origins=["*"],
            )

    def test_production_accepts_valid_config(self):
        settings = AppSettings(
            environment="production",
            api_key="real-secret-key",
            cors_origins=["https://app.example.com"],
        )
        assert settings.environment == "production"

    def test_development_allows_defaults(self):
        """Development environment accepts any api_key and cors_origins."""
        settings = AppSettings(environment="development", api_key="changeme", cors_origins=["*"])
        assert settings.api_key == "changeme"
        assert settings.cors_origins == ["*"]

    def test_production_rejects_wildcard_among_other_origins(self):
        with pytest.raises(ValidationError, match="cors_origins"):
            AppSettings(
                environment="production",
                api_key="real-key",
                cors_origins=["https://app.example.com", "*"],
            )
