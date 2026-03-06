from __future__ import annotations

from src.applications.deep_search.config import DeepSearchSettings


class TestDeepSearchSettings:
    def test_defaults(self):
        settings = DeepSearchSettings()
        # app_name may be overridden by .env, so check deep-search-specific fields
        assert settings.academic_max_results == 10
        assert settings.deep_crawler_max_depth == 2
        assert settings.deep_crawler_max_pages == 10
        assert settings.research_max_iterations == 3
        assert settings.research_max_time_seconds == 300
        assert settings.research_per_agent_timeout_seconds == 120.0
        assert settings.stream_max_concurrent_requests == 100
        assert settings.code_execution_enabled is False
        assert settings.docker_network_disabled is True
        assert settings.docker_image == "python:3.11-slim"

    def test_custom_values(self):
        settings = DeepSearchSettings(
            llm_model="gpt-4o-mini",
            research_max_iterations=5,
            code_execution_enabled=True,
            academic_max_results=20,
        )
        assert settings.llm_model == "gpt-4o-mini"
        assert settings.research_max_iterations == 5
        assert settings.code_execution_enabled is True
        assert settings.academic_max_results == 20

    def test_extends_app_settings(self):
        settings = DeepSearchSettings()
        # Inherits from AppSettings
        assert hasattr(settings, "host")
        assert hasattr(settings, "port")
        assert hasattr(settings, "api_key")
        assert hasattr(settings, "rate_limit_requests")
