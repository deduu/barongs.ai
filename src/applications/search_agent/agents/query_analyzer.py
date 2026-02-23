from __future__ import annotations

import json

from src.core.interfaces.agent import Agent
from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMMessage, LLMRequest
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult

SYSTEM_PROMPT = """You are a query analyzer. Classify the user's message and return JSON.

Rules:
- If the query asks for factual information, current events, or anything that requires web search, classify as "search".
- If the query is conversational (greetings, opinions, simple math, general knowledge you're confident about), classify as "direct".
- For search queries, generate 1-3 refined search queries optimized for web search.

Return ONLY valid JSON in this exact format:
{"query_type": "search"|"direct", "refined_queries": ["query1", "query2"]}"""


class QueryAnalyzerAgent(Agent):
    """Classifies user queries as 'search' or 'direct' and generates refined search queries."""

    def __init__(self, llm_provider: LLMProvider, model: str = "gpt-4o") -> None:
        self._llm = llm_provider
        self._model = model

    @property
    def name(self) -> str:
        return "query_analyzer"

    @property
    def description(self) -> str:
        return "Analyzes and classifies user queries for routing."

    async def run(self, context: AgentContext) -> AgentResult:
        request = LLMRequest(
            messages=[LLMMessage(role="user", content=context.user_message)],
            model=self._model,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.0,
            max_tokens=256,
        )

        response = await self._llm.generate(request)

        try:
            parsed = json.loads(response.content)
            query_type = parsed.get("query_type", "search")
            refined_queries = parsed.get("refined_queries", [])
        except (json.JSONDecodeError, KeyError):
            # Default to search with original query when parsing fails
            query_type = "search"
            refined_queries = [context.user_message]

        return AgentResult(
            agent_name=self.name,
            response=response.content,
            metadata={
                "query_type": query_type,
                "refined_queries": refined_queries,
            },
            token_usage=response.usage,
        )
