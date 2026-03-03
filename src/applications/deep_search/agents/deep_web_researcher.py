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


class DeepWebResearcherAgent(Agent):
    """Multi-hop web researcher: search -> crawl -> score -> extract findings."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        search_tool: Tool,
        deep_crawler_tool: Tool,
        source_scorer_tool: Tool,
        model: str = "gpt-4o",
        max_sources: int = 5,
    ) -> None:
        self._llm = llm_provider
        self._search_tool = search_tool
        self._crawler_tool = deep_crawler_tool
        self._scorer_tool = source_scorer_tool
        self._model = model
        self._max_sources = max_sources

    @property
    def name(self) -> str:
        return "deep_web_researcher"

    @property
    def description(self) -> str:
        return "Deep web research with crawling and knowledge extraction."

    async def run(self, context: AgentContext) -> AgentResult:
        query = context.user_message
        entity_grounding = context.metadata.get("entity_grounding", {})
        entity_name = entity_grounding.get("name", "")
        entity_desc = entity_grounding.get("description", "")

        # Step 1: Web search
        search_result = await self._search_tool.execute(
            ToolInput(tool_name=self._search_tool.name, parameters={"query": query})
        )

        if not search_result.success or not search_result.output:
            return AgentResult(
                agent_name=self.name,
                response="No web results found.",
                metadata={"findings": []},
            )

        results: list[dict[str, Any]] = search_result.output[: self._max_sources]
        findings: list[dict[str, Any]] = []

        for item in results:
            url = item.get("url", "")
            if not url:
                continue

            # Step 2: Deep crawl
            crawl_result = await self._crawler_tool.execute(
                ToolInput(tool_name=self._crawler_tool.name, parameters={"url": url})
            )

            content = ""
            if crawl_result.success and crawl_result.output:
                pages = crawl_result.output.get("pages", [])
                content = "\n".join(p.get("content", "")[:3000] for p in pages[:3])

            if not content:
                content = item.get("snippet", "")

            # Step 3: Score source
            score_result = await self._scorer_tool.execute(
                ToolInput(tool_name=self._scorer_tool.name, parameters={"url": url})
            )
            credibility = score_result.output if score_result.success else {}

            # Step 4: Extract finding via LLM (with entity grounding)
            entity_instruction = ""
            if entity_name:
                entity_instruction = (
                    f"\n\nIMPORTANT: The target entity is: {entity_name}"
                    f"\nDescription: {entity_desc}"
                    f"\nONLY extract findings that are specifically about this entity. "
                    f"If the content is about a DIFFERENT entity with a similar name, "
                    f"respond with exactly: {_NOT_RELEVANT_SENTINEL}"
                )

            try:
                request = LLMRequest(
                    messages=[
                        LLMMessage(
                            role="user",
                            content=f"Extract key findings relevant to: {query}\n\n"
                            f"Source: {url}\nContent: {content[:5000]}"
                            f"{entity_instruction}",
                        )
                    ],
                    model=self._model,
                    system_prompt=(
                        "Extract a comprehensive, detailed summary of the key findings. "
                        "Include specific facts, data points, and technical details. "
                        "Be thorough — capture all relevant information from the source. "
                        "If the content is not about the target entity, respond with: "
                        f"{_NOT_RELEVANT_SENTINEL}"
                    ),
                    temperature=0.2,
                    max_tokens=800,
                )
                response = await self._llm.generate(request)

                if _NOT_RELEVANT_SENTINEL in response.content.upper():
                    logger.debug("Filtered irrelevant finding from: %s", url)
                    continue

                findings.append(
                    {
                        "finding_id": f"f_{uuid.uuid4().hex[:8]}",
                        "content": response.content,
                        "source_url": url,
                        "confidence": credibility.get("overall_score", 0.5),
                        "methodology_tag": "secondary_web",
                        "credibility": credibility,
                        "citations": [item.get("title", url)],
                        "entity_match": True,
                    }
                )
            except Exception:
                logger.debug("Failed to extract finding from: %s", url)

        return AgentResult(
            agent_name=self.name,
            response=f"Found {len(findings)} web findings.",
            metadata={"findings": findings},
        )
