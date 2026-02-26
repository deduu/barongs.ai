"""Tests for RAGTool — Tool adapter wrapping HybridRetriever."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.core.interfaces.tool import Tool
from src.core.models.context import ToolInput
from src.core.rag.models import Document, ResultSource, SearchResult
from src.core.rag.retriever import HybridRetriever
from src.core.rag.tool import RAGTool


@pytest.fixture
def mock_retriever() -> AsyncMock:
    retriever = AsyncMock(spec=HybridRetriever)
    retriever.retrieve.return_value = [
        SearchResult(
            document=Document(id="d1", content="Python is great"),
            score=0.95,
            source=ResultSource.DENSE,
        ),
        SearchResult(
            document=Document(id="d2", content="FastAPI is fast"),
            score=0.85,
            source=ResultSource.DENSE,
        ),
    ]
    return retriever


@pytest.fixture
def rag_tool(mock_retriever: AsyncMock) -> RAGTool:
    return RAGTool(retriever=mock_retriever)


class TestRAGToolProperties:
    def test_is_a_tool(self, rag_tool):
        assert isinstance(rag_tool, Tool)

    def test_name(self, rag_tool):
        assert rag_tool.name == "rag_retrieve"

    def test_description(self, rag_tool):
        assert "retrieval" in rag_tool.description.lower()

    def test_input_schema(self, rag_tool):
        schema = rag_tool.input_schema
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "query" in schema["required"]


class TestRAGToolExecute:
    async def test_execute_returns_results(self, rag_tool, mock_retriever):
        tool_input = ToolInput(
            tool_name="rag_retrieve",
            parameters={"query": "python"},
        )
        result = await rag_tool.execute(tool_input)
        assert result.success is True
        assert result.tool_name == "rag_retrieve"
        assert len(result.output) == 2

    async def test_execute_passes_query_to_retriever(self, rag_tool, mock_retriever):
        tool_input = ToolInput(
            tool_name="rag_retrieve",
            parameters={"query": "python programming"},
        )
        await rag_tool.execute(tool_input)
        mock_retriever.retrieve.assert_called_once_with(
            "python programming", top_k=5, filters=None
        )

    async def test_execute_passes_top_k(self, rag_tool, mock_retriever):
        tool_input = ToolInput(
            tool_name="rag_retrieve",
            parameters={"query": "test", "top_k": 10},
        )
        await rag_tool.execute(tool_input)
        mock_retriever.retrieve.assert_called_once_with(
            "test", top_k=10, filters=None
        )

    async def test_execute_passes_filters(self, rag_tool, mock_retriever):
        tool_input = ToolInput(
            tool_name="rag_retrieve",
            parameters={"query": "test", "filters": {"source": "web"}},
        )
        await rag_tool.execute(tool_input)
        mock_retriever.retrieve.assert_called_once_with(
            "test", top_k=5, filters={"source": "web"}
        )

    async def test_execute_empty_results(self, rag_tool, mock_retriever):
        mock_retriever.retrieve.return_value = []
        tool_input = ToolInput(
            tool_name="rag_retrieve",
            parameters={"query": "nothing"},
        )
        result = await rag_tool.execute(tool_input)
        assert result.success is True
        assert result.output == []

    async def test_execute_handles_retriever_error(self, rag_tool, mock_retriever):
        mock_retriever.retrieve.side_effect = RuntimeError("connection failed")
        tool_input = ToolInput(
            tool_name="rag_retrieve",
            parameters={"query": "test"},
        )
        result = await rag_tool.execute(tool_input)
        assert result.success is False
        assert "connection failed" in result.error

    async def test_output_contains_serialized_results(self, rag_tool, mock_retriever):
        tool_input = ToolInput(
            tool_name="rag_retrieve",
            parameters={"query": "python"},
        )
        result = await rag_tool.execute(tool_input)
        first = result.output[0]
        assert first["id"] == "d1"
        assert first["content"] == "Python is great"
        assert first["score"] == 0.95
