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

PLANNER_SYSTEM_PROMPT = """You are a research planning agent. Given a user query, decompose it into a DAG of research sub-tasks.

{entity_context}

Return ONLY valid JSON with this structure:
{{
  "tasks": [
    {{
      "task_id": "t1",
      "query": "specific sub-question about {entity_name}",
      "task_type": "secondary_web|secondary_academic|primary_code|fact_check|reflection",
      "depends_on": [],
      "agent_name": "deep_web_researcher|academic_researcher|data_analyst|fact_checker|reflection"
    }}
  ]
}}

Rules:
- Each task must have a unique task_id
- fact_check tasks should depend on research tasks
- reflection tasks should depend on all other tasks
- Use secondary_web for general web research
- Use secondary_academic for scholarly/scientific topics
- Use primary_code for data analysis or computation tasks
- IMPORTANT: All search queries MUST include disambiguating terms for the target entity to avoid results about different entities with similar names
- Keep tasks focused and specific"""


class ResearchPlannerAgent(Agent):
    """Decomposes a user query into a DAG of research sub-tasks."""

    def __init__(self, llm_provider: LLMProvider, model: str = "gpt-4o") -> None:
        self._llm = llm_provider
        self._model = model

    @property
    def name(self) -> str:
        return "research_planner"

    @property
    def description(self) -> str:
        return "Decomposes queries into a research plan DAG."

    async def run(self, context: AgentContext) -> AgentResult:
        try:
            entity_grounding = context.metadata.get("entity_grounding", {})
            entity_name = entity_grounding.get("name", "the subject")
            entity_desc = entity_grounding.get("description", "")
            key_attrs = entity_grounding.get("key_attributes", [])

            entity_context = ""
            if entity_desc:
                entity_context = (
                    f"TARGET ENTITY: {entity_name}\n"
                    f"Description: {entity_desc}\n"
                    f"Key attributes: {', '.join(key_attrs)}\n"
                    f"All research tasks MUST be specifically about this entity. "
                    f"Include disambiguating terms in every search query."
                )

            system_prompt = PLANNER_SYSTEM_PROMPT.format(
                entity_context=entity_context,
                entity_name=entity_name,
            )

            request = LLMRequest(
                messages=[LLMMessage(role="user", content=context.user_message)],
                model=self._model,
                system_prompt=system_prompt,
                temperature=0.2,
            )
            response = await self._llm.generate(request)

            plan_data = self._parse_plan(response.content)

            return AgentResult(
                agent_name=self.name,
                response=f"Created research plan with {len(plan_data.get('tasks', []))} tasks",
                metadata={
                    "research_plan": {
                        "original_query": context.user_message,
                        "tasks": plan_data.get("tasks", []),
                        "max_iterations": 3,
                        "entity_grounding": entity_grounding,
                    },
                },
                token_usage=response.usage,
            )
        except Exception as exc:
            logger.error("Research planner failed: %s", exc)
            return AgentResult(
                agent_name=self.name,
                response=f"Error creating research plan: {exc}",
                metadata={"error": str(exc)},
            )

    @staticmethod
    def _parse_plan(content: str) -> dict[str, Any]:
        """Extract JSON from LLM response, handling markdown code blocks."""
        # Strip markdown code fences
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if match:
            content = match.group(1)
        result: dict[str, Any] = json.loads(content.strip())
        return result
