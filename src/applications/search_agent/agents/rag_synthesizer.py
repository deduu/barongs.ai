from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from src.core.interfaces.agent import Agent
from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMMessage, LLMRequest
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult

RAG_SYSTEM_PROMPT_TEMPLATE = """You are a helpful assistant that answers questions using ONLY the provided knowledge base documents. You must cite your sources.

IMPORTANT RULES:
1. Use inline citations in the format [Doc N] where N corresponds to the document number listed below.
2. Every factual claim must have at least one citation.
3. Be thorough and detailed — provide a comprehensive answer that covers all relevant aspects.
4. Use headings, bullet points, or numbered lists to organize your response when appropriate.
5. If the documents contain conflicting information, mention the disagreement and cite both sides.
6. If no documents are relevant to the question, say so honestly — do NOT make up information.
7. NEVER use information from outside the provided documents.
8. At the end of your response, add a "---" separator followed by a "### Sources" section listing all cited documents.

KNOWLEDGE BASE DOCUMENTS:
{sources_text}

Answer the question using only the documents above, with inline [Doc N] citations."""


class RAGSynthesizerAgent(Agent):
    """Synthesizes an answer from knowledge base documents retrieved via RAG."""

    def __init__(self, llm_provider: LLMProvider, model: str = "gpt-4o") -> None:
        self._llm = llm_provider
        self._model = model

    @property
    def name(self) -> str:
        return "rag-synthesizer"

    @property
    def description(self) -> str:
        return "Synthesizes knowledge base documents into a cited response."

    def _format_rag_sources(self, sources: list[dict[str, Any]]) -> str:
        """Format RAG search results for the system prompt."""
        if not sources:
            return "No documents available."

        parts: list[str] = []
        for i, source in enumerate(sources, start=1):
            title = source.get("metadata", {}).get("title", f"Document {i}")
            content = source.get("content", "")[:4000]
            score = source.get("score", 0.0)
            parts.append(
                f"[Doc {i}] {title} (relevance: {score:.2f})\n"
                f"Content: {content}\n"
            )
        return "\n".join(parts)

    async def run(self, context: AgentContext) -> AgentResult:
        sources: list[dict[str, Any]] = context.metadata.get("rag_sources", [])
        sources_text = self._format_rag_sources(sources)
        system_prompt = RAG_SYSTEM_PROMPT_TEMPLATE.format(sources_text=sources_text)

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
            metadata={"rag_sources": sources},
            token_usage=response.usage,
        )

    async def stream_run(self, context: AgentContext) -> AsyncIterator[str]:
        """Yield response tokens as they arrive from the LLM."""
        sources: list[dict[str, Any]] = context.metadata.get("rag_sources", [])
        sources_text = self._format_rag_sources(sources)
        system_prompt = RAG_SYSTEM_PROMPT_TEMPLATE.format(sources_text=sources_text)

        request = LLMRequest(
            messages=[LLMMessage(role="user", content=context.user_message)],
            model=self._model,
            system_prompt=system_prompt,
            temperature=0.3,
        )

        async for token in self._llm.stream(request):
            yield token
