from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.interfaces.agent import Agent
from src.core.interfaces.memory import Memory
from src.core.interfaces.tool import Tool
from src.core.models.config import AppSettings
from src.core.models.context import AgentContext, ToolInput
from src.core.models.results import AgentResult, ToolResult

# --- Stub implementations for testing ---


class StubAgent(Agent):
    """Agent that returns a fixed response."""

    @property
    def name(self) -> str:
        return "stub_agent"

    async def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            response=f"Echo: {context.user_message}",
        )


class StubTool(Tool):
    """Tool that returns fixed output."""

    @property
    def name(self) -> str:
        return "stub_tool"

    @property
    def description(self) -> str:
        return "A stub tool for testing"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"query": {"type": "string"}}}

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        return ToolResult(tool_name=self.name, output="stub_output")


class StubMemory(Memory):
    """In-memory dict-backed memory for testing."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        return self._store.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    async def search(
        self, query: str, *, top_k: int = 5, namespace: str | None = None
    ) -> list[dict[str, Any]]:
        results = []
        for k, v in self._store.items():
            if query.lower() in str(v).lower():
                results.append({"key": k, "value": v, "score": 1.0})
        return results[:top_k]


# --- Fixtures ---


@pytest.fixture
def settings() -> AppSettings:
    return AppSettings(app_name="test", debug=True, api_key="test-key")


@pytest.fixture
def agent_context() -> AgentContext:
    return AgentContext(user_message="Hello, world!")


@pytest.fixture
def stub_agent() -> StubAgent:
    return StubAgent()


@pytest.fixture
def stub_tool() -> StubTool:
    return StubTool()


@pytest.fixture
def stub_memory() -> StubMemory:
    return StubMemory()


@pytest_asyncio.fixture
async def async_client(settings: AppSettings) -> AsyncGenerator[AsyncClient, None]:
    from src.core.server.factory import create_app

    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
