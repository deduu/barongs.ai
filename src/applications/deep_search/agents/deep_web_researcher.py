from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from src.applications.deep_search.query_utils import (
    select_primary_query,
    source_mentions_entity,
    source_mentions_query_focus,
    source_supports_entity_description,
)
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

    _EXTRACTION_DETAIL_TOKENS = {"low": 400, "medium": 800, "high": 1200}
    _DEFAULT_CRAWL_MAX_DEPTH = 1
    _DEFAULT_CRAWL_MAX_PAGES = 3
    _DEFAULT_PAGE_TIMEOUT_SECONDS = 6.0
    _CRAWL_STEP_TIMEOUT_SECONDS = 12.0
    _SCORE_STEP_TIMEOUT_SECONDS = 6.0
    _EXTRACT_STEP_TIMEOUT_SECONDS = 20.0
    _DEADLINE_SAFETY_BUFFER_SECONDS = 0.75

    @staticmethod
    def _bounded_int(
        value: Any,
        default: int,
        *,
        min_value: int,
        max_value: int,
    ) -> int:
        if isinstance(value, int):
            return max(min_value, min(max_value, value))
        return default

    @staticmethod
    def _bounded_float(
        value: Any,
        default: float,
        *,
        min_value: float,
        max_value: float,
    ) -> float:
        if isinstance(value, (int, float)):
            numeric = float(value)
            return max(min_value, min(max_value, numeric))
        return default

    @staticmethod
    def _remaining_seconds(deadline: float | None) -> float | None:
        if deadline is None:
            return None
        remaining = deadline - asyncio.get_running_loop().time()
        return max(0.0, remaining)

    def _step_timeout(
        self,
        *,
        deadline: float | None,
        default_timeout: float,
        minimum_remaining: float,
    ) -> float | None:
        remaining = self._remaining_seconds(deadline)
        if remaining is None:
            return default_timeout
        if remaining < minimum_remaining:
            return None
        return min(default_timeout, remaining)

    async def run(self, context: AgentContext) -> AgentResult:
        query = context.user_message
        max_sources = self._bounded_int(
            context.metadata.get("max_sources", self._max_sources),
            self._max_sources,
            min_value=1,
            max_value=15,
        )
        extraction_detail = context.metadata.get("extraction_detail", "medium")
        extract_max_tokens = self._EXTRACTION_DETAIL_TOKENS.get(extraction_detail, 800)
        entity_grounding = context.metadata.get("entity_grounding", {})
        entity_name = entity_grounding.get("name", "")
        entity_desc = entity_grounding.get("description", "")
        search_query = select_primary_query(query, entity_name)
        crawl_max_depth = self._bounded_int(
            context.metadata.get(
                "crawl_depth",
                context.metadata.get(
                    "crawl_max_depth",
                    context.metadata.get("deep_crawler_max_depth", self._DEFAULT_CRAWL_MAX_DEPTH),
                ),
            ),
            self._DEFAULT_CRAWL_MAX_DEPTH,
            min_value=0,
            max_value=5,
        )
        crawl_max_pages = self._bounded_int(
            context.metadata.get(
                "crawl_max_pages",
                context.metadata.get("deep_crawler_max_pages", self._DEFAULT_CRAWL_MAX_PAGES),
            ),
            self._DEFAULT_CRAWL_MAX_PAGES,
            min_value=1,
            max_value=15,
        )
        crawl_page_timeout_seconds = self._bounded_float(
            context.metadata.get(
                "crawl_page_timeout_seconds",
                context.metadata.get(
                    "deep_crawler_page_timeout_seconds",
                    self._DEFAULT_PAGE_TIMEOUT_SECONDS,
                ),
            ),
            self._DEFAULT_PAGE_TIMEOUT_SECONDS,
            min_value=1.0,
            max_value=20.0,
        )
        agent_timeout_seconds = self._bounded_float(
            context.metadata.get("agent_timeout_seconds"),
            0.0,
            min_value=0.0,
            max_value=3600.0,
        )
        deadline: float | None = None
        if agent_timeout_seconds > 0:
            deadline = (
                asyncio.get_running_loop().time()
                + max(0.0, agent_timeout_seconds - self._DEADLINE_SAFETY_BUFFER_SECONDS)
            )
        logger.info(
            "Deep web researcher started: query=%s search_query=%s max_sources=%s crawl_depth=%s crawl_pages=%s",
            query[:160],
            search_query[:160],
            max_sources,
            crawl_max_depth,
            crawl_max_pages,
        )

        search_timeout = self._step_timeout(
            deadline=deadline,
            default_timeout=self._CRAWL_STEP_TIMEOUT_SECONDS,
            minimum_remaining=0.5,
        )
        if search_timeout is None:
            return AgentResult(
                agent_name=self.name,
                response="No time remaining before web search could start.",
                metadata={"findings": [], "attempted_sources": [], "timed_out": True},
            )
        try:
            search_result = await asyncio.wait_for(
                self._search_tool.execute(
                    ToolInput(tool_name=self._search_tool.name, parameters={"query": search_query})
                ),
                timeout=search_timeout,
            )
        except asyncio.TimeoutError:
            return AgentResult(
                agent_name=self.name,
                response=f"Web search step timed out after {search_timeout:.1f}s.",
                metadata={"findings": [], "attempted_sources": [], "timed_out": True},
            )

        if not search_result.success or not search_result.output:
            return AgentResult(
                agent_name=self.name,
                response="No web results found.",
                metadata={"findings": [], "attempted_sources": []},
            )

        results: list[dict[str, Any]] = search_result.output[:max_sources]
        findings: list[dict[str, Any]] = []
        attempted_sources: list[dict[str, Any]] = []
        budget_exhausted = False

        for item in results:
            remaining = self._remaining_seconds(deadline)
            if remaining is not None and remaining < 1.0:
                budget_exhausted = True
                break

            url = item.get("url", "")
            if not url:
                continue
            source_record: dict[str, Any] = {
                "url": url,
                "title": item.get("title", ""),
                "status": "queued",
            }
            attempted_sources.append(source_record)
            logger.info("Deep web researcher source queued: url=%s", url)

            crawl_timeout = self._step_timeout(
                deadline=deadline,
                default_timeout=self._CRAWL_STEP_TIMEOUT_SECONDS,
                minimum_remaining=1.0,
            )
            if crawl_timeout is None:
                source_record["status"] = "skipped_timeout_budget"
                budget_exhausted = True
                break
            try:
                crawl_result = await asyncio.wait_for(
                    self._crawler_tool.execute(
                        ToolInput(
                            tool_name=self._crawler_tool.name,
                            parameters={
                                "url": url,
                                "max_depth": crawl_max_depth,
                                "max_pages": crawl_max_pages,
                                "page_timeout_seconds": crawl_page_timeout_seconds,
                            },
                        )
                    ),
                    timeout=crawl_timeout,
                )
            except asyncio.TimeoutError:
                source_record["status"] = "crawl_timeout"
                logger.info("Deep web researcher crawl timeout: url=%s", url)
                continue

            content = ""
            if crawl_result.success and crawl_result.output:
                pages = crawl_result.output.get("pages", [])
                content = "\n".join(p.get("content", "")[:3000] for p in pages[:3])
            source_record["crawl_success"] = bool(crawl_result.success)

            if not content:
                content = item.get("snippet", "")

            score_timeout = self._step_timeout(
                deadline=deadline,
                default_timeout=self._SCORE_STEP_TIMEOUT_SECONDS,
                minimum_remaining=0.8,
            )
            if score_timeout is None:
                source_record["status"] = "skipped_timeout_budget"
                budget_exhausted = True
                break
            try:
                score_result = await asyncio.wait_for(
                    self._scorer_tool.execute(
                        ToolInput(tool_name=self._scorer_tool.name, parameters={"url": url})
                    ),
                    timeout=score_timeout,
                )
            except asyncio.TimeoutError:
                source_record["status"] = "scoring_timeout"
                logger.info("Deep web researcher scoring timeout: url=%s", url)
                continue
            credibility = score_result.output if score_result.success else {}

            entity_instruction = ""
            if entity_name:
                entity_instruction = (
                    f"\n\nIMPORTANT: The target entity is: {entity_name}"
                    f"\nDescription: {entity_desc}"
                    f"\nONLY extract findings that are specifically about this entity. "
                    f"If the content is CLEARLY about a different entity with a similar name, "
                    f"respond with exactly: {_NOT_RELEVANT_SENTINEL}"
                )

            try:
                extract_timeout = self._step_timeout(
                    deadline=deadline,
                    default_timeout=self._EXTRACT_STEP_TIMEOUT_SECONDS,
                    minimum_remaining=1.0,
                )
                if extract_timeout is None:
                    source_record["status"] = "skipped_timeout_budget"
                    budget_exhausted = True
                    break
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
                        "Be thorough. Capture only source-supported information from the source. "
                        "Only respond with NOT_RELEVANT when the source is clearly about a different "
                        "entity than the target. "
                        "If the content is not about the target entity, respond with: "
                        f"{_NOT_RELEVANT_SENTINEL}"
                    ),
                    temperature=0.2,
                    max_tokens=extract_max_tokens,
                )
                response = await asyncio.wait_for(
                    self._llm.generate(request),
                    timeout=extract_timeout,
                )

                if _NOT_RELEVANT_SENTINEL in response.content.upper():
                    likely_relevant = source_mentions_entity(
                        entity_name,
                        item.get("title", ""),
                        item.get("snippet", ""),
                        content,
                    )
                    supported_by_focus = source_mentions_query_focus(
                        query,
                        entity_name,
                        item.get("title", ""),
                        item.get("snippet", ""),
                        content,
                    ) or source_supports_entity_description(
                        entity_desc,
                        item.get("title", ""),
                        item.get("snippet", ""),
                        content,
                    )
                    if not likely_relevant or not supported_by_focus:
                        logger.debug("Filtered irrelevant finding from: %s", url)
                        source_record["status"] = "filtered_irrelevant"
                        continue

                    retry_request = LLMRequest(
                        messages=[
                            LLMMessage(
                                role="user",
                                content=(
                                    f"The source explicitly mentions {entity_name}. "
                                    f"Extract only the source-supported details relevant to: {query}\n\n"
                                    f"Source: {url}\n"
                                    f"Title: {item.get('title', '')}\n"
                                    f"Snippet: {item.get('snippet', '')}\n"
                                    f"Content: {content[:5000]}"
                                ),
                            )
                        ],
                        model=self._model,
                        system_prompt=(
                            "Use cautious wording and summarize only the evidence present in the source. "
                            "Return NOT_RELEVANT only if the source clearly refers to a different entity."
                        ),
                        temperature=0.1,
                        max_tokens=min(600, extract_max_tokens),
                    )
                    retry_response = await asyncio.wait_for(
                        self._llm.generate(retry_request),
                        timeout=extract_timeout,
                    )
                    if _NOT_RELEVANT_SENTINEL in retry_response.content.upper():
                        logger.debug("Filtered irrelevant finding after retry: %s", url)
                        source_record["status"] = "filtered_irrelevant"
                        continue
                    response = retry_response
                    source_record["status"] = "finding_extracted_retry"

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
                if source_record["status"] == "queued":
                    source_record["status"] = "finding_extracted"
                logger.info("Deep web researcher finding extracted: url=%s", url)
            except asyncio.TimeoutError:
                source_record["status"] = "extraction_timeout"
                logger.info("Deep web researcher extraction timeout: url=%s", url)
            except Exception:
                logger.debug("Failed to extract finding from: %s", url)
                source_record["status"] = "extraction_error"
                logger.info("Deep web researcher extraction error: url=%s", url)

        response = f"Found {len(findings)} web findings from {len(attempted_sources)} sources."
        if budget_exhausted:
            response += " Stopped early due to time budget."
        logger.info(
            "Deep web researcher finished: findings=%s attempted=%s budget_exhausted=%s",
            len(findings),
            len(attempted_sources),
            budget_exhausted,
        )
        return AgentResult(
            agent_name=self.name,
            response=response,
            metadata={
                "findings": findings,
                "attempted_sources": attempted_sources,
                "timed_out": budget_exhausted,
            },
        )
