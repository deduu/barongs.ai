from __future__ import annotations

import logging
import uuid
from typing import Any

from src.core.interfaces.agent import Agent
from src.core.interfaces.tool import Tool
from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMMessage, LLMRequest
from src.core.models.context import AgentContext, ToolInput
from src.core.models.results import AgentResult

logger = logging.getLogger(__name__)

_NOT_RELEVANT_SENTINEL = "NOT_RELEVANT"


class AcademicResearcherAgent(Agent):
    """Searches academic papers and extracts findings with credibility scores."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        academic_search_tool: Tool,
        source_scorer_tool: Tool,
        model: str = "gpt-4o",
    ) -> None:
        self._llm = llm_provider
        self._academic_tool = academic_search_tool
        self._scorer_tool = source_scorer_tool
        self._model = model

    @property
    def name(self) -> str:
        return "academic_researcher"

    @property
    def description(self) -> str:
        return "Searches academic papers and extracts findings."

    async def run(self, context: AgentContext) -> AgentResult:
        query = context.user_message
        entity_grounding = context.metadata.get("entity_grounding", {})
        entity_name = entity_grounding.get("name", "")
        entity_desc = entity_grounding.get("description", "")

        # Step 1: Search academic sources
        search_result = await self._academic_tool.execute(
            ToolInput(tool_name=self._academic_tool.name, parameters={"query": query})
        )

        if not search_result.success or not search_result.output:
            return AgentResult(
                agent_name=self.name,
                response="No academic results found.",
                metadata={"findings": []},
            )

        papers: list[dict[str, Any]] = search_result.output
        findings: list[dict[str, Any]] = []

        for paper in papers[:10]:
            # Score the source
            score_result = await self._scorer_tool.execute(
                ToolInput(
                    tool_name=self._scorer_tool.name,
                    parameters={
                        "url": paper.get("url", ""),
                        "year": paper.get("year"),
                        "citation_count": paper.get("citation_count", 0),
                        "is_peer_reviewed": paper.get("source") in ("arxiv", "semantic_scholar"),
                    },
                )
            )

            credibility = score_result.output if score_result.success else {}

            # Extract finding via LLM (with entity grounding)
            entity_instruction = ""
            if entity_name:
                entity_instruction = (
                    f"\n\nIMPORTANT: The target entity is: {entity_name}"
                    f"\nDescription: {entity_desc}"
                    f"\nONLY extract findings that are specifically about this entity. "
                    f"If the paper is about a DIFFERENT entity with a similar name, "
                    f"respond with exactly: {_NOT_RELEVANT_SENTINEL}"
                )

            try:
                request = LLMRequest(
                    messages=[
                        LLMMessage(
                            role="user",
                            content=f"Extract key findings from this paper relevant to: {query}\n\n"
                            f"Title: {paper.get('title', '')}\n"
                            f"Abstract: {paper.get('abstract', '')[:3000]}"
                            f"{entity_instruction}",
                        )
                    ],
                    model=self._model,
                    system_prompt=(
                        "You are a research assistant. Extract a comprehensive, detailed summary "
                        "of the key findings. Include methodology, results, specific data points, "
                        "and conclusions. Be thorough. "
                        "If the content is not about the target entity, respond with: "
                        f"{_NOT_RELEVANT_SENTINEL}"
                    ),
                    temperature=0.2,
                    max_tokens=800,
                )
                response = await self._llm.generate(request)

                if _NOT_RELEVANT_SENTINEL in response.content.upper():
                    logger.debug("Filtered irrelevant academic finding: %s", paper.get("title"))
                    continue

                findings.append(
                    {
                        "finding_id": f"f_{uuid.uuid4().hex[:8]}",
                        "content": response.content,
                        "source_url": paper.get("url", ""),
                        "confidence": credibility.get("overall_score", 0.5),
                        "methodology_tag": "secondary_academic",
                        "credibility": credibility,
                        "citations": [paper.get("title", "")],
                        "entity_match": True,
                    }
                )
            except Exception:
                logger.debug("Failed to extract finding from paper: %s", paper.get("title"))

        return AgentResult(
            agent_name=self.name,
            response=f"Found {len(findings)} academic findings.",
            metadata={"findings": findings},
        )
