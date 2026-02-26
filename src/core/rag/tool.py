"""RAGTool — Tool adapter that wraps a HybridRetriever for agent use."""

from __future__ import annotations

import time
from typing import Any

from src.core.interfaces.tool import Tool
from src.core.models.context import ToolInput
from src.core.models.results import ToolResult
from src.core.rag.retriever import HybridRetriever


class RAGTool(Tool):
    """Tool adapter exposing hybrid retrieval to agents.

    Agents call this tool with a query string and receive ranked
    document results from the configured retrieval pipeline.
    """

    def __init__(self, retriever: HybridRetriever) -> None:
        self._retriever = retriever

    @property
    def name(self) -> str:
        return "rag_retrieve"

    @property
    def description(self) -> str:
        return (
            "Search the knowledge base using hybrid retrieval "
            "(dense + sparse + reranker)."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "top_k": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of results to return",
                },
                "filters": {
                    "type": "object",
                    "description": "Optional metadata filters",
                },
            },
            "required": ["query"],
        }

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        params = tool_input.parameters
        query: str = params["query"]
        top_k: int = params.get("top_k", 5)
        filters: dict[str, Any] | None = params.get("filters")

        start = time.perf_counter()
        try:
            results = await self._retriever.retrieve(
                query, top_k=top_k, filters=filters
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            output = [
                {
                    "id": r.document.id,
                    "content": r.document.content,
                    "score": r.score,
                    "source": r.source.value,
                    "metadata": r.document.metadata,
                }
                for r in results
            ]

            return ToolResult(
                tool_name=self.name,
                output=output,
                success=True,
                duration_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return ToolResult(
                tool_name=self.name,
                output=None,
                success=False,
                error=str(exc),
                duration_ms=elapsed_ms,
            )
