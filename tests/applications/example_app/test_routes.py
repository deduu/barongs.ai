"""Integration tests for example app routes."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.applications.example_app.main import create_example_app


@pytest_asyncio.fixture
async def app_client() -> AsyncGenerator[AsyncClient, None]:
    app = create_example_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestExampleAppRoutes:
    async def test_health(self, app_client):
        response = await app_client.get("/health")
        assert response.status_code == 200

    async def test_chat_endpoint(self, app_client):
        response = await app_client.post(
            "/api/chat",
            json={"message": "Hello!"},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "Hello!" in data["response"]

    async def test_chat_requires_auth(self, app_client):
        response = await app_client.post(
            "/api/chat",
            json={"message": "Hello!"},
        )
        assert response.status_code == 401
