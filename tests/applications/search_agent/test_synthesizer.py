from __future__ import annotations

from unittest.mock import AsyncMock

from src.applications.search_agent.agents.synthesizer import SynthesizerAgent
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext


class TestSynthesizerAgent:
    def _make_agent(self, llm_content: str = "Synthesized response") -> SynthesizerAgent:
        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(
            return_value=LLMResponse(content=llm_content, model="gpt-4o")
        )
        return SynthesizerAgent(llm_provider=mock_provider, model="gpt-4o")

    def test_name(self):
        agent = self._make_agent()
        assert agent.name == "synthesizer"

    async def test_synthesize_with_sources(self):
        cited_response = (
            "Python is a programming language [1]. It was created by Guido van Rossum [2]."
        )
        agent = self._make_agent(cited_response)
        ctx = AgentContext(
            user_message="What is Python?",
            metadata={
                "sources": [
                    {
                        "url": "https://example.com/1",
                        "title": "Python Overview",
                        "snippet": "Python is...",
                        "content": "Python is a high-level language.",
                        "index": 1,
                    },
                    {
                        "url": "https://example.com/2",
                        "title": "Python History",
                        "snippet": "Created by...",
                        "content": "Created by Guido van Rossum.",
                        "index": 2,
                    },
                ]
            },
        )
        result = await agent.run(ctx)

        assert "[1]" in result.response
        assert "[2]" in result.response
        assert result.metadata["sources"] == ctx.metadata["sources"]

    async def test_synthesize_with_no_sources(self):
        agent = self._make_agent("I couldn't find any relevant information.")
        ctx = AgentContext(
            user_message="What is Python?",
            metadata={"sources": []},
        )
        result = await agent.run(ctx)

        assert result.response is not None
        assert result.agent_name == "synthesizer"

    async def test_system_prompt_includes_citation_instructions(self):
        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(
            return_value=LLMResponse(content="response", model="gpt-4o")
        )
        agent = SynthesizerAgent(llm_provider=mock_provider, model="gpt-4o")

        ctx = AgentContext(
            user_message="test",
            metadata={
                "sources": [
                    {
                        "url": "https://example.com",
                        "title": "Test",
                        "snippet": "test",
                        "content": "test content",
                        "index": 1,
                    }
                ]
            },
        )
        await agent.run(ctx)

        # Verify the system prompt was passed to the LLM
        call_args = mock_provider.generate.call_args[0][0]
        assert call_args.system_prompt is not None
        assert "[1]" in call_args.system_prompt or "citation" in call_args.system_prompt.lower()
