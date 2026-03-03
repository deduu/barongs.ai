from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.applications.search_agent.agents.rag_synthesizer import RAGSynthesizerAgent
from src.applications.search_agent.rag_routes import RAGChatRequest
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext


class TestRAGSynthesizerTemperatureOverride:
    """Verify that the RAG synthesizer reads temperature from context.metadata."""

    async def test_uses_default_temperature(self) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(
            return_value=LLMResponse(content="ok", model="gpt-4o")
        )
        agent = RAGSynthesizerAgent(llm_provider=llm, model="gpt-4o")

        ctx = AgentContext(user_message="test", metadata={"rag_sources": []})
        await agent.run(ctx)

        request = llm.generate.call_args[0][0]
        assert request.temperature == pytest.approx(0.3)

    async def test_temperature_override_from_metadata(self) -> None:
        llm = AsyncMock()
        llm.generate = AsyncMock(
            return_value=LLMResponse(content="ok", model="gpt-4o")
        )
        agent = RAGSynthesizerAgent(llm_provider=llm, model="gpt-4o")

        ctx = AgentContext(
            user_message="test",
            metadata={"rag_sources": [], "temperature": 0.6},
        )
        await agent.run(ctx)

        request = llm.generate.call_args[0][0]
        assert request.temperature == pytest.approx(0.6)

    async def test_stream_run_uses_temperature_override(self) -> None:
        llm = AsyncMock()
        captured_request = None

        async def mock_stream(req: object) -> object:
            nonlocal captured_request
            captured_request = req
            for t in ["a"]:
                yield t

        llm.stream = mock_stream
        agent = RAGSynthesizerAgent(llm_provider=llm, model="gpt-4o")

        ctx = AgentContext(
            user_message="test",
            metadata={"rag_sources": [], "temperature": 0.0},
        )
        async for _ in agent.stream_run(ctx):
            pass

        assert captured_request is not None
        assert captured_request.temperature == pytest.approx(0.0)


class TestRAGChatRequestValidation:
    """Verify RAGChatRequest model accepts and validates new fields."""

    def test_accepts_temperature(self) -> None:
        req = RAGChatRequest(query="test", temperature=0.5)
        assert req.temperature == 0.5

    def test_accepts_dense_weight(self) -> None:
        req = RAGChatRequest(query="test", dense_weight=0.8)
        assert req.dense_weight == 0.8

    def test_accepts_enable_reranker(self) -> None:
        req = RAGChatRequest(query="test", enable_reranker=False)
        assert req.enable_reranker is False

    def test_defaults_are_none(self) -> None:
        req = RAGChatRequest(query="test")
        assert req.temperature is None
        assert req.dense_weight is None
        assert req.enable_reranker is None

    def test_temperature_validation_rejects_out_of_range(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RAGChatRequest(query="test", temperature=-0.1)

    def test_dense_weight_validation_rejects_out_of_range(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RAGChatRequest(query="test", dense_weight=1.5)

    def test_backward_compatible_request(self) -> None:
        """Ensure old-style requests (query + top_k only) still work."""
        req = RAGChatRequest(query="What is AI?", top_k=10)
        assert req.query == "What is AI?"
        assert req.top_k == 10
        assert req.temperature is None
        assert req.dense_weight is None
        assert req.enable_reranker is None
