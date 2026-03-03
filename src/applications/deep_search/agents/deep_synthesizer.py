from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from src.core.interfaces.agent import Agent
from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMMessage, LLMRequest
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult

SYNTH_SYSTEM_PROMPT = """You are a deep research synthesizer. Create a comprehensive research report from the findings.

{entity_context}

Structure your response as:
# Executive Summary
Brief overview of key findings about {entity_name}.

## [Topic Section 1]
Detailed analysis with inline citations [source_url].

## [Topic Section 2]
...

## Methodology Notes
How the research was conducted.

## Limitations
What gaps or uncertainties remain.

FINDINGS:
{findings_text}

IMPORTANT RULES:
- Every claim must reference a finding.
- ONLY include information that is specifically about {entity_name}.
- If a finding appears to be about a different entity with a similar name, DISCARD it and note this in the Limitations section.
- If no relevant findings exist, say so honestly rather than speculating."""


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

        system_prompt = SYNTH_SYSTEM_PROMPT.format(
            findings_text=findings_text,
            entity_context=entity_context,
            entity_name=entity_name,
        )

        return LLMRequest(
            messages=[LLMMessage(role="user", content=context.user_message)],
            model=self._model,
            system_prompt=system_prompt,
            temperature=0.3,
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
