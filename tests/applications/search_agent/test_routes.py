from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.applications.search_agent.config import SearchAgentSettings
from src.applications.search_agent.routes import create_router
from src.core.interfaces.orchestrator import Orchestrator
from src.core.models.results import AgentResult
from src.core.server.factory import create_app


@pytest.fixture
def settings() -> SearchAgentSettings:
    return SearchAgentSettings(
        app_name="test-search",
        api_key="test-key",
        llm_api_key="test-llm-key",
        search_api_key="test-search-key",
    )


@pytest.fixture
def mock_orchestrator() -> Orchestrator:
    mock = AsyncMock(spec=Orchestrator)
    mock.run = AsyncMock(
        return_value=AgentResult(
            agent_name="search_pipeline",
            response="Python is a language [1].",
            metadata={
                "sources": [
                    {
                        "url": "https://example.com",
                        "title": "Python Docs",
                        "snippet": "Python is...",
                        "content": "Full content",
                        "index": 1,
                    }
                ],
                "query_type": "search",
            },
        )
    )
    return mock  # type: ignore[return-value]


@pytest.fixture
async def async_client(
    settings: SearchAgentSettings, mock_orchestrator: Orchestrator
) -> AsyncClient:
    app = create_app(settings)
    router = create_router(mock_orchestrator, settings)
    app.include_router(router)

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestSearchRoutes:
    async def test_search_endpoint(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/search",
            json={"query": "What is Python?"},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "sources" in data
        assert data["response"] == "Python is a language [1]."

    async def test_search_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/search",
            json={"query": "test"},
        )
        assert response.status_code == 401

    async def test_search_invalid_auth(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/search",
            json={"query": "test"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 403

    async def test_chat_endpoint(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/chat",
            json={"message": "Hello!"},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    async def test_search_validation_error(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/search",
            json={},  # Missing required field
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 422
