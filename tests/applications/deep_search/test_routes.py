from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.applications.deep_search.models.streaming import DeepSearchEventType
from src.applications.deep_search.routes import create_router
from src.core.models.results import AgentResult


def _create_app(orchestrator=None, pipeline=None, settings=None):
    """Create a test app with the deep search router."""
    from src.applications.deep_search.config import DeepSearchSettings

    settings = settings or DeepSearchSettings()
    orchestrator = orchestrator or AsyncMock()
    orchestrator.run = orchestrator.run if hasattr(orchestrator, 'run') else AsyncMock(
        return_value=AgentResult(
            agent_name="research_dag",
            response="Test result",
            metadata={"findings": [], "sources": []},
        )
    )

    pipeline = pipeline or AsyncMock()

    router = create_router(orchestrator, settings, pipeline=pipeline)
    app = FastAPI()
    app.include_router(router)
    return app


class TestDeepSearchRoutes:
    def test_sync_search(self):
        orchestrator = AsyncMock()
        orchestrator.run = AsyncMock(return_value=AgentResult(
            agent_name="research_dag",
            response="Python uses GIL",
            metadata={"findings": [{"id": "f1"}], "sources": ["web_researcher"]},
        ))

        app = _create_app(orchestrator=orchestrator)
        client = TestClient(app)

        response = client.post(
            "/api/deep-search",
            json={"query": "What is Python GIL?"},
            headers={"X-API-Key": "changeme"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "executive_summary" in data

    def test_stream_search(self):
        pipeline = AsyncMock()

        async def mock_stream(ctx):
            yield {"event": DeepSearchEventType.PLANNING, "data": {"status": "planning"}}
            yield {"event": DeepSearchEventType.CHUNK, "data": {"token": "Hello"}}
            yield {"event": DeepSearchEventType.DONE, "data": {"response": "Hello"}}

        pipeline.stream_run = mock_stream

        app = _create_app(pipeline=pipeline)
        client = TestClient(app)

        with client.stream(
            "POST",
            "/api/deep-search/stream",
            json={"query": "test"},
            headers={"X-API-Key": "changeme"},
        ) as response:
            assert response.status_code == 200
            # SSE content type
            assert "text/event-stream" in response.headers.get("content-type", "")

    def test_missing_query_returns_422(self):
        app = _create_app()
        client = TestClient(app)

        response = client.post(
            "/api/deep-search",
            json={},
            headers={"X-API-Key": "changeme"},
        )

        assert response.status_code == 422
