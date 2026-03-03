from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from src.applications.deep_search.models.research_mode import ResearchMode
from src.applications.deep_search.prompts.synthesizer_prompts import SYNTH_PROMPTS
from src.core.interfaces.agent import Agent
from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMMessage, LLMRequest
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult


class DeepSynthesizerAgent(Agent):
    """Produces final research report with structured sections and streaming support."""

    def __init__(self, llm_provider: LLMProvider, model: str = "gpt-4o") -> None:
        self._llm = llm_provider
        self._model = model

    @property
    def name(self) -> str:
        return "deep_synthesizer"

    @property
    def description(self) -> str:
        return "Synthesizes research findings into a comprehensive report."

    def _format_findings(self, findings: list[dict[str, Any]]) -> str:
        if not findings:
            return (
                "WARNING: No verified findings are available about this specific entity. "
                "Do NOT fabricate information. Instead, explain what was searched and that "
                "insufficient verified information was found."
            )
        parts: list[str] = []
        for f in findings:
            parts.append(
                f"[{f.get('finding_id', 'unknown')}] (confidence: {f.get('confidence', 'N/A')})\n"
                f"Source: {f.get('source_url', 'unknown')}\n"
                f"Content: {f.get('content', '')[:4000]}\n"
            )
        return "\n".join(parts)

    def _build_request(self, context: AgentContext) -> LLMRequest:
        findings: list[dict[str, Any]] = context.metadata.get("findings", [])
        entity_grounding = context.metadata.get("entity_grounding", {})
        entity_name = entity_grounding.get("name", "the subject")
        entity_desc = entity_grounding.get("description", "")

        # Filter out findings flagged as misattributed
        misattributed_ids = set(context.metadata.get("misattributed_ids", []))
        relevant_findings = [f for f in findings if f.get("finding_id") not in misattributed_ids]

        entity_context = ""
        if entity_desc:
            source_urls = entity_grounding.get("source_urls", [])
            entity_context = (
                f"TARGET ENTITY: {entity_name}\n"
                f"Description: {entity_desc}\n"
                f"Primary sources: {', '.join(source_urls)}\n"
            )

        findings_text = self._format_findings(relevant_findings)

        custom_sections = context.metadata.get("custom_sections")
        if custom_sections:
            # User edited the outline — build prompt from their section structure
            section_instructions = "\n".join(
                f"## {s['heading']}\n{s.get('description', '')}"
                for s in custom_sections
            )
            system_prompt = (
                f"You are a deep research synthesizer. Create a comprehensive research report "
                f"from the findings.\n\n{entity_context}\n\n"
                f"Structure your response using EXACTLY these sections:\n\n{section_instructions}\n\n"
                f"FINDINGS:\n{findings_text}\n\n"
                f"IMPORTANT RULES:\n"
                f"- Every claim must reference a finding.\n"
                f"- ONLY include information that is specifically about {entity_name}.\n"
                f"- If a finding appears to be about a different entity, DISCARD it.\n"
                f"- If no relevant findings exist, say so honestly rather than speculating."
            )
        else:
            research_mode = ResearchMode(context.metadata.get("research_mode", "general"))
            template = SYNTH_PROMPTS[research_mode]
            system_prompt = template.format(
                findings_text=findings_text,
                entity_context=entity_context,
                entity_name=entity_name,
            )

        temperature = context.metadata.get("temperature", 0.3)

        return LLMRequest(
            messages=[LLMMessage(role="user", content=context.user_message)],
            model=self._model,
            system_prompt=system_prompt,
            temperature=temperature,
        )

    async def run(self, context: AgentContext) -> AgentResult:
        request = self._build_request(context)
        response = await self._llm.generate(request)

        return AgentResult(
            agent_name=self.name,
            response=response.content,
            metadata={"findings": context.metadata.get("findings", [])},
            token_usage=response.usage,
        )

    async def stream_run(self, context: AgentContext) -> AsyncIterator[str]:
        """Yield response tokens as they arrive from the LLM."""
        request = self._build_request(context)
        async for token in self._llm.stream(request):
            yield token
