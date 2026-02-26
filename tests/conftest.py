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
from src.core.rag.interfaces.embedder import Embedder
from src.core.rag.interfaces.reranker import Reranker
from src.core.rag.interfaces.sparse_retriever import SparseRetriever
from src.core.rag.interfaces.vector_store import VectorStore
from src.core.rag.models import Document, ResultSource, SearchResult

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


class StubEmbedder(Embedder):
    """Embedder that returns deterministic vectors."""

    @property
    def name(self) -> str:
        return "stub_embedder"

    @property
    def dimension(self) -> int:
        return 3

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t)), 0.1, 0.2] for t in texts]


class StubVectorStore(VectorStore):
    """In-memory vector store for testing."""

    def __init__(self) -> None:
        self._docs: dict[str, Document] = {}

    @property
    def name(self) -> str:
        return "stub_vector_store"

    async def upsert(self, documents: list[Document]) -> None:
        for doc in documents:
            self._docs[doc.id] = doc

    async def search(
        self,
        vector: list[float],
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        return [
            SearchResult(document=doc, score=0.9, source=ResultSource.DENSE)
            for doc in list(self._docs.values())[:top_k]
        ]

    async def delete(self, ids: list[str]) -> None:
        for doc_id in ids:
            self._docs.pop(doc_id, None)


class StubSparseRetriever(SparseRetriever):
    """Keyword-matching sparse retriever for testing."""

    def __init__(self) -> None:
        self._docs: dict[str, Document] = {}

    @property
    def name(self) -> str:
        return "stub_sparse"

    async def index(self, documents: list[Document]) -> None:
        for doc in documents:
            self._docs[doc.id] = doc

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        return [
            SearchResult(document=doc, score=0.8, source=ResultSource.SPARSE)
            for doc in list(self._docs.values())[:top_k]
            if query.lower() in doc.content.lower()
        ]

    async def delete(self, ids: list[str]) -> None:
        for doc_id in ids:
            self._docs.pop(doc_id, None)


class StubReranker(Reranker):
    """Reranker that boosts scores and tags as RERANKED."""

    @property
    def name(self) -> str:
        return "stub_reranker"

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        *,
        top_k: int = 5,
    ) -> list[SearchResult]:
        reranked = [
            SearchResult(
                document=r.document,
                score=r.score + 0.05,
                source=ResultSource.RERANKED,
            )
            for r in results[:top_k]
        ]
        return sorted(reranked, key=lambda r: r.score, reverse=True)


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


@pytest.fixture
def stub_embedder() -> StubEmbedder:
    return StubEmbedder()


@pytest.fixture
def stub_vector_store() -> StubVectorStore:
    return StubVectorStore()


@pytest.fixture
def stub_sparse_retriever() -> StubSparseRetriever:
    return StubSparseRetriever()


@pytest.fixture
def stub_reranker() -> StubReranker:
    return StubReranker()


@pytest_asyncio.fixture
async def async_client(settings: AppSettings) -> AsyncGenerator[AsyncClient, None]:
    from src.core.server.factory import create_app

    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
