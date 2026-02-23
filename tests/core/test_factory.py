"""Tests for the FastAPI app factory."""

from __future__ import annotations

from fastapi import FastAPI

from src.core.models.config import AppSettings
from src.core.server.factory import create_app


class TestAppFactory:
    def test_returns_fastapi_instance(self):
        app = create_app()
        assert isinstance(app, FastAPI)

    def test_uses_custom_settings(self):
        settings = AppSettings(app_name="custom-app", debug=True)
        app = create_app(settings)
        assert app.title == "custom-app"
        assert app.debug is True

    async def test_health_endpoint(self, async_client):
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_ready_endpoint(self, async_client):
        response = await async_client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
