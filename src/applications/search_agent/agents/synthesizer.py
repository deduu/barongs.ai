from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from src.core.interfaces.agent import Agent
from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMMessage, LLMRequest
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult

SYSTEM_PROMPT_TEMPLATE = """You are a research assistant that synthesizes information from web sources into a clear, comprehensive answer.

IMPORTANT RULES:
1. Use inline citations in the format [1], [2], etc. to reference your sources.
2. Every factual claim must have at least one citation.
3. Be comprehensive but concise.
4. If sources conflict, mention the disagreement and cite both sides.
5. If no sources are relevant, say so honestly.

AVAILABLE SOURCES:
{sources_text}

Respond with a well-structured answer using the citations above."""


class SynthesizerAgent(Agent):
    """Synthesizes web sources into a cited response."""

    def __init__(self, llm_provider: LLMProvider, model: str = "gpt-4o") -> None:
        self._llm = llm_provider
        self._model = model

    @property
    def name(self) -> str:
        return "synthesizer"

    @property
    def description(self) -> str:
        return "Synthesizes search results into a cited response."

    def _format_sources(self, sources: list[dict[str, Any]]) -> str:
        """Format sources for the system prompt."""
        parts: list[str] = []
        for source in sources:
            parts.append(
                f"[{source['index']}] {source['title']}\n"
                f"URL: {source['url']}\n"
                f"Content: {source['content'][:2000]}\n"
            )
        return "\n".join(parts) if parts else "No sources available."

    async def run(self, context: AgentContext) -> AgentResult:
        sources: list[dict[str, Any]] = context.metadata.get("sources", [])
        sources_text = self._format_sources(sources)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(sources_text=sources_text)

        request = LLMRequest(
            messages=[LLMMessage(role="user", content=context.user_message)],
            model=self._model,
            system_prompt=system_prompt,
            temperature=0.3,
        )

        response = await self._llm.generate(request)

        return AgentResult(
            agent_name=self.name,
            response=response.content,
            metadata={"sources": sources},
            token_usage=response.usage,
        )

    async def stream_run(self, context: AgentContext) -> AsyncIterator[str]:
        """Yield response tokens as they arrive from the LLM."""
        sources: list[dict[str, Any]] = context.metadata.get("sources", [])
        sources_text = self._format_sources(sources)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(sources_text=sources_text)

        request = LLMRequest(
            messages=[LLMMessage(role="user", content=context.user_message)],
            model=self._model,
            system_prompt=system_prompt,
            temperature=0.3,
        )

        async for token in self._llm.stream(request):
            yield token
