from __future__ import annotations

from unittest.mock import patch

from fastapi import FastAPI

from src.applications.deep_search.config import DeepSearchSettings
from src.applications.deep_search.main import create_deep_search_app


class TestDeepSearchAppFactory:
    @patch("src.applications.deep_search.main.OpenAICompatibleProvider")
    def test_creates_fastapi_app(self, mock_oai):
        mock_oai.return_value.name = "openai"
        mock_oai.return_value.generate = None
        mock_oai.return_value.stream = None

        settings = DeepSearchSettings(
            llm_provider="openai",
            llm_base_url="http://localhost:11434/v1",
            llm_api_key="test-key",
        )
        app = create_deep_search_app(settings)

        assert isinstance(app, FastAPI)

    @patch("src.applications.deep_search.main.OpenAICompatibleProvider")
    def test_includes_deep_search_routes(self, mock_oai):
        mock_oai.return_value.name = "openai"
        mock_oai.return_value.generate = None
        mock_oai.return_value.stream = None

        settings = DeepSearchSettings(
            llm_provider="openai",
            llm_base_url="http://localhost:11434/v1",
            llm_api_key="test-key",
        )
        app = create_deep_search_app(settings)

        # Check routes exist
        route_paths = [r.path for r in app.routes]
        assert "/api/deep-search" in route_paths
        assert "/api/deep-search/stream" in route_paths
