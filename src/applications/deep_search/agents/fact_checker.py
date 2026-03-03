from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.core.interfaces.agent import Agent
from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMMessage, LLMRequest
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult

logger = logging.getLogger(__name__)

FACT_CHECK_PROMPT = """You are a fact-checking agent. Review the findings and:
1. Identify key claims
2. Check for contradictions between findings
3. Adjust confidence scores based on cross-references
4. Check if each finding is about the correct target entity

{entity_context}

Return ONLY valid JSON:
{{
  "checked_findings": [
    {{"finding_id": "...", "adjusted_confidence": 0.0-1.0, "notes": "...", "entity_match": true}}
  ],
  "contradictions": [
    {{"finding_ids": ["f1", "f2"], "description": "..."}}
  ],
  "misattributions": [
    {{"finding_id": "...", "reason": "This finding is about [wrong entity], not the target"}}
  ]
}}"""


class FactCheckerAgent(Agent):
    """Cross-references findings, detects contradictions, adjusts confidence."""

    def __init__(self, llm_provider: LLMProvider, model: str = "gpt-4o") -> None:
        self._llm = llm_provider
        self._model = model

    @property
    def name(self) -> str:
        return "fact_checker"

    @property
    def description(self) -> str:
        return "Cross-references findings and detects contradictions."

    async def run(self, context: AgentContext) -> AgentResult:
        all_findings_groups: list[Any] = context.metadata.get("all_findings", [])
        all_findings: list[dict[str, Any]] = []
        for group in all_findings_groups:
            if isinstance(group, list):
                all_findings.extend(group)

        if not all_findings:
            return AgentResult(
                agent_name=self.name,
                response="No findings to check.",
                metadata={
                    "checked_findings": [],
                    "contradictions": [],
                    "misattributions": [],
                    "misattributed_ids": [],
                },
            )

        entity_grounding = context.metadata.get("entity_grounding", {})
        entity_name = entity_grounding.get("name", "")
        entity_desc = entity_grounding.get("description", "")

        entity_context = ""
        if entity_name:
            entity_context = (
                f"TARGET ENTITY: {entity_name}\n"
                f"Description: {entity_desc}\n"
                f"Any finding that is about a DIFFERENT entity (even with a similar name) "
                f"must be marked with entity_match: false and listed in misattributions."
            )

        findings_text = json.dumps(all_findings, indent=2, default=str)

        try:
            system_prompt = FACT_CHECK_PROMPT.format(entity_context=entity_context)

            request = LLMRequest(
                messages=[
                    LLMMessage(
                        role="user",
                        content=f"Fact-check these findings:\n\n{findings_text[:8000]}",
                    )
                ],
                model=self._model,
                system_prompt=system_prompt,
                temperature=0.2,
            )
            response = await self._llm.generate(request)

            result_data = self._parse_json(response.content)

            misattributions = result_data.get("misattributions", [])
            misattributed_ids = [m["finding_id"] for m in misattributions if "finding_id" in m]

            return AgentResult(
                agent_name=self.name,
                response=f"Checked {len(all_findings)} findings. {len(misattributed_ids)} misattributed.",
                metadata={
                    "checked_findings": result_data.get("checked_findings", []),
                    "contradictions": result_data.get("contradictions", []),
                    "misattributions": misattributions,
                    "misattributed_ids": misattributed_ids,
                },
                token_usage=response.usage,
            )
        except Exception as exc:
            logger.error("Fact checker failed: %s", exc)
            return AgentResult(
                agent_name=self.name,
                response=f"Fact checking error: {exc}",
                metadata={
                    "checked_findings": [],
                    "contradictions": [],
                    "misattributions": [],
                    "misattributed_ids": [],
                    "error": str(exc),
                },
            )

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if match:
            content = match.group(1)
        result: dict[str, Any] = json.loads(content.strip())
        return result
