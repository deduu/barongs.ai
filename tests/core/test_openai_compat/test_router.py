from __future__ import annotations

import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.core.models.config import AppSettings
from src.core.models.results import AgentResult
from src.core.server.openai_compat.registry import ModelRegistry
from src.core.server.openai_compat.router import create_openai_router

API_KEY = "test-key-123"
AUTH_HEADER = {"Authorization": f"Bearer {API_KEY}"}


def _make_settings() -> AppSettings:
    return AppSettings(api_key=API_KEY, openai_auth_enabled=True)


def _make_agent_result(response: str = "Hello!") -> AgentResult:
    return AgentResult(
        agent_name="test-agent",
        response=response,
        token_usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    )


def _make_mock_orchestrator(response: str = "Hello!") -> AsyncMock:
    orch = AsyncMock()
    orch.run = AsyncMock(return_value=_make_agent_result(response))
    return orch


async def _make_stream_agent(tokens: list[str]) -> AsyncMock:
    """Create a mock agent whose stream_run yields the given tokens."""
    agent = AsyncMock()

    async def _stream_run(context: object) -> AsyncIterator[str]:
        for t in tokens:
            yield t

    agent.stream_run = _stream_run
    return agent


def _make_app(
    registry: ModelRegistry,
    settings: AppSettings | None = None,
) -> FastAPI:
    settings = settings or _make_settings()
    app = FastAPI()
    router = create_openai_router(registry, settings)
    app.include_router(router)
    return app


@pytest.fixture
def settings() -> AppSettings:
    return _make_settings()


@pytest.fixture
def mock_orchestrator() -> AsyncMock:
    return _make_mock_orchestrator()


@pytest.fixture
def registry(mock_orchestrator: AsyncMock) -> ModelRegistry:
    reg = ModelRegistry()
    reg.register("test-model", mock_orchestrator)
    return reg


@pytest.fixture
async def client(registry: ModelRegistry, settings: AppSettings) -> AsyncClient:
    app = _make_app(registry, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c  # type: ignore[misc]


class TestListModels:
    async def test_returns_registered_models(self, client: AsyncClient) -> None:
        resp = await client.get("/v1/models", headers=AUTH_HEADER)
        assert resp.status_code == 200
        body = resp.json()
        assert body["object"] == "list"
        assert len(body["data"]) == 1
        assert body["data"][0]["id"] == "test-model"
        assert body["data"][0]["object"] == "model"

    async def test_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/v1/models")
        assert resp.status_code == 401

    async def test_multiple_models(self, settings: AppSettings) -> None:
        reg = ModelRegistry()
        reg.register("model-a", _make_mock_orchestrator())
        reg.register("model-b", _make_mock_orchestrator())
        app = _make_app(reg, settings)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/v1/models", headers=AUTH_HEADER)
        ids = {m["id"] for m in resp.json()["data"]}
        assert ids == {"model-a", "model-b"}


class TestChatCompletionsNonStreaming:
    async def test_returns_openai_format(
        self, client: AsyncClient, mock_orchestrator: AsyncMock
    ) -> None:
        resp = await client.post(
            "/v1/chat/completions",
            headers=AUTH_HEADER,
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hi"}],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["object"] == "chat.completion"
        assert body["choices"][0]["message"]["role"] == "assistant"
        assert body["choices"][0]["message"]["content"] == "Hello!"
        assert body["choices"][0]["finish_reason"] == "stop"
        assert body["usage"]["total_tokens"] == 15

    async def test_unknown_model_returns_404(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/v1/chat/completions",
            headers=AUTH_HEADER,
            json={
                "model": "nonexistent",
                "messages": [{"role": "user", "content": "Hi"}],
            },
        )
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body["detail"]

    async def test_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hi"}],
            },
        )
        assert resp.status_code == 401

    async def test_passes_context_to_orchestrator(
        self, client: AsyncClient, mock_orchestrator: AsyncMock
    ) -> None:
        await client.post(
            "/v1/chat/completions",
            headers=AUTH_HEADER,
            json={
                "model": "test-model",
                "messages": [
                    {"role": "system", "content": "Be helpful"},
                    {"role": "user", "content": "What is AI?"},
                ],
            },
        )
        mock_orchestrator.run.assert_called_once()
        context = mock_orchestrator.run.call_args[0][0]
        assert context.user_message == "What is AI?"
        assert any(
            h["role"] == "system" for h in context.conversation_history
        )


class TestChatCompletionsStreaming:
    async def test_streaming_with_streamable_agent(
        self, settings: AppSettings
    ) -> None:
        orch = _make_mock_orchestrator()
        stream_agent = await _make_stream_agent(["Hel", "lo ", "world"])

        reg = ModelRegistry()
        reg.register(
            "stream-model", orch, streamable_agent=stream_agent
        )
        app = _make_app(reg, settings)
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/v1/chat/completions",
                headers=AUTH_HEADER,
                json={
                    "model": "stream-model",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": True,
                },
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        # Parse SSE lines
        lines = resp.text.strip().split("\n")
        data_lines = [line.removeprefix("data: ") for line in lines if line.startswith("data: ")]

        # First chunk should have role
        first = json.loads(data_lines[0])
        assert first["choices"][0]["delta"]["role"] == "assistant"

        # Content chunks
        content_chunks = data_lines[1:-2]  # skip role, finish, and [DONE]
        content = "".join(
            json.loads(c)["choices"][0]["delta"]["content"] for c in content_chunks
        )
        assert content == "Hello world"

        # Last data chunk before [DONE] should have finish_reason
        finish = json.loads(data_lines[-2])
        assert finish["choices"][0]["finish_reason"] == "stop"

        # Final line is [DONE]
        assert data_lines[-1] == "[DONE]"

    async def test_streaming_fallback_no_streamable_agent(
        self, client: AsyncClient
    ) -> None:
        """When no streamable_agent is registered, stream=true still works."""
        resp = await client.post(
            "/v1/chat/completions",
            headers=AUTH_HEADER,
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True,
            },
        )
        assert resp.status_code == 200

        lines = resp.text.strip().split("\n")
        data_lines = [line.removeprefix("data: ") for line in lines if line.startswith("data: ")]

        # Should contain: role chunk, content chunk, finish chunk, [DONE]
        assert len(data_lines) >= 4
        assert data_lines[-1] == "[DONE]"

        # The content chunk should contain the full response
        content_chunk = json.loads(data_lines[1])
        assert content_chunk["choices"][0]["delta"]["content"] == "Hello!"


class TestNoAuthMode:
    async def test_models_without_auth(self, settings: AppSettings) -> None:
        no_auth_settings = AppSettings(api_key="secret", openai_auth_enabled=False)
        reg = ModelRegistry()
        reg.register("m", _make_mock_orchestrator())
        app = _make_app(reg, no_auth_settings)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/v1/models")
        assert resp.status_code == 200
        assert resp.json()["data"][0]["id"] == "m"

    async def test_chat_completions_without_auth(self) -> None:
        no_auth_settings = AppSettings(api_key="secret", openai_auth_enabled=False)
        reg = ModelRegistry()
        reg.register("m", _make_mock_orchestrator())
        app = _make_app(reg, no_auth_settings)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/v1/chat/completions",
                json={
                    "model": "m",
                    "messages": [{"role": "user", "content": "Hi"}],
                },
            )
        assert resp.status_code == 200
        assert resp.json()["choices"][0]["message"]["content"] == "Hello!"
