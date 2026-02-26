from __future__ import annotations

from unittest.mock import AsyncMock

from src.applications.search_agent.agents.rag_synthesizer import RAGSynthesizerAgent
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext


class TestRAGSynthesizerAgent:
    def _make_agent(self, llm_content: str = "Answer from knowledge base.") -> RAGSynthesizerAgent:
        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(
            return_value=LLMResponse(content=llm_content, model="gpt-4o")
        )
        return RAGSynthesizerAgent(llm_provider=mock_provider, model="gpt-4o")

    def test_name(self) -> None:
        agent = self._make_agent()
        assert agent.name == "rag-synthesizer"

    def test_description(self) -> None:
        agent = self._make_agent()
        assert "knowledge base" in agent.description.lower()

    async def test_run_with_rag_sources(self) -> None:
        cited = "The answer is 42 [Doc 1]. This was confirmed [Doc 2]."
        agent = self._make_agent(cited)
        ctx = AgentContext(
            user_message="What is the answer?",
            metadata={
                "rag_sources": [
                    {
                        "id": "chunk-0",
                        "content": "The answer to life is 42.",
                        "score": 0.95,
                        "source": "dense",
                        "metadata": {"title": "Guide", "chunk_index": 0},
                    },
                    {
                        "id": "chunk-1",
                        "content": "42 was confirmed by Deep Thought.",
                        "score": 0.88,
                        "source": "reranked",
                        "metadata": {"title": "History", "chunk_index": 1},
                    },
                ]
            },
        )
        result = await agent.run(ctx)

        assert "42" in result.response
        assert result.agent_name == "rag-synthesizer"
        assert result.metadata["rag_sources"] == ctx.metadata["rag_sources"]

    async def test_run_with_no_sources(self) -> None:
        agent = self._make_agent("I don't have relevant documents to answer this.")
        ctx = AgentContext(
            user_message="What is quantum gravity?",
            metadata={"rag_sources": []},
        )
        result = await agent.run(ctx)

        assert result.response is not None
        assert result.agent_name == "rag-synthesizer"

    async def test_system_prompt_includes_rag_instructions(self) -> None:
        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(
            return_value=LLMResponse(content="response", model="gpt-4o")
        )
        agent = RAGSynthesizerAgent(llm_provider=mock_provider, model="gpt-4o")

        ctx = AgentContext(
            user_message="test query",
            metadata={
                "rag_sources": [
                    {
                        "id": "doc-0",
                        "content": "Test document content.",
                        "score": 0.9,
                        "source": "dense",
                        "metadata": {"title": "Test Doc"},
                    }
                ]
            },
        )
        await agent.run(ctx)

        call_args = mock_provider.generate.call_args[0][0]
        assert call_args.system_prompt is not None
        assert "knowledge base" in call_args.system_prompt.lower()
        assert "Test document content." in call_args.system_prompt

    async def test_stream_run_yields_tokens(self) -> None:
        mock_provider = AsyncMock()
        tokens = ["Hello", " from", " knowledge", " base."]

        async def mock_stream(_request: object) -> object:
            for token in tokens:
                yield token

        mock_provider.stream = mock_stream
        agent = RAGSynthesizerAgent(llm_provider=mock_provider, model="gpt-4o")

        ctx = AgentContext(
            user_message="test query",
            metadata={
                "rag_sources": [
                    {
                        "id": "doc-0",
                        "content": "Knowledge base content.",
                        "score": 0.9,
                        "source": "dense",
                        "metadata": {},
                    }
                ]
            },
        )
        collected: list[str] = []
        async for token in agent.stream_run(ctx):
            collected.append(token)

        assert collected == tokens

    async def test_format_rag_sources(self) -> None:
        agent = self._make_agent()
        sources = [
            {
                "id": "chunk-0",
                "content": "Some content here.",
                "score": 0.95,
                "source": "dense",
                "metadata": {"title": "My Doc", "chunk_index": 0},
            },
        ]
        text = agent._format_rag_sources(sources)

        assert "[Doc 1]" in text
        assert "My Doc" in text
        assert "Some content here." in text

    async def test_format_rag_sources_empty(self) -> None:
        agent = self._make_agent()
        text = agent._format_rag_sources([])
        assert "no documents" in text.lower()

    async def test_token_usage_propagated(self) -> None:
        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(
            return_value=LLMResponse(
                content="answer",
                model="gpt-4o",
                usage={"prompt_tokens": 100, "completion_tokens": 50},
            )
        )
        agent = RAGSynthesizerAgent(llm_provider=mock_provider, model="gpt-4o")
        ctx = AgentContext(
            user_message="test",
            metadata={"rag_sources": []},
        )
        result = await agent.run(ctx)
        assert result.token_usage == {"prompt_tokens": 100, "completion_tokens": 50}
