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

REFLECTION_PROMPT = """You are a research reflection agent. Review the findings and identify:
1. Knowledge gaps — what questions remain unanswered?
2. Confidence assessment — is the overall evidence sufficient?
3. Follow-up tasks — what additional research would fill the gaps?

Return ONLY valid JSON:
{
  "gaps": ["description of gap 1", "..."],
  "new_tasks": [
    {
      "task_id": "t_followup_1",
      "query": "specific follow-up question",
      "task_type": "secondary_web|secondary_academic|primary_code",
      "depends_on": [],
      "agent_name": "deep_web_researcher|academic_researcher|data_analyst"
    }
  ],
  "overall_confidence": 0.0-1.0
}

If findings are sufficient (confidence > 0.8), return empty gaps and new_tasks."""


class ReflectionAgent(Agent):
    """Reviews findings, identifies gaps, and generates follow-up tasks."""

    def __init__(self, llm_provider: LLMProvider, model: str = "gpt-4o") -> None:
        self._llm = llm_provider
        self._model = model

    @property
    def name(self) -> str:
        return "reflection"

    @property
    def description(self) -> str:
        return "Reviews findings, identifies gaps, and proposes follow-up research."

    async def run(self, context: AgentContext) -> AgentResult:
        all_findings_groups: list[Any] = context.metadata.get("all_findings", [])
        all_findings: list[dict[str, Any]] = []
        for group in all_findings_groups:
            if isinstance(group, list):
                all_findings.extend(group)

        findings_text = (
            json.dumps(all_findings, indent=2, default=str) if all_findings else "No findings yet."
        )

        try:
            request = LLMRequest(
                messages=[
                    LLMMessage(
                        role="user",
                        content=f"Review these research findings:\n\n{findings_text[:8000]}",
                    )
                ],
                model=self._model,
                system_prompt=REFLECTION_PROMPT,
                temperature=0.3,
            )
            response = await self._llm.generate(request)

            result_data = self._parse_json(response.content)

            return AgentResult(
                agent_name=self.name,
                response=f"Reflection: {len(result_data.get('gaps', []))} gaps found.",
                metadata={
                    "gaps": result_data.get("gaps", []),
                    "new_tasks": result_data.get("new_tasks", []),
                    "overall_confidence": result_data.get("overall_confidence", 0.5),
                },
                token_usage=response.usage,
            )
        except Exception as exc:
            logger.error("Reflection failed: %s", exc)
            return AgentResult(
                agent_name=self.name,
                response=f"Reflection error: {exc}",
                metadata={"gaps": [], "new_tasks": [], "overall_confidence": 0.0},
            )

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if match:
            content = match.group(1)
        result: dict[str, Any] = json.loads(content.strip())
        return result
