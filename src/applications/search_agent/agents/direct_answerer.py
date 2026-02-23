from __future__ import annotations

from typing import Any

from src.core.interfaces.agent import Agent
from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMMessage, LLMRequest
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult

SYSTEM_PROMPT = """You are a helpful, conversational AI assistant. Answer the user's question directly and concisely. If you're not sure about something, say so. You do not have access to web search in this mode."""


class DirectAnswererAgent(Agent):
    """Handles non-search queries with direct LLM responses."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        model: str = "gpt-4o",
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> None:
        self._llm = llm_provider
        self._model = model
        self._conversation_history = conversation_history or []

    @property
    def name(self) -> str:
        return "direct_answerer"

    @property
    def description(self) -> str:
        return "Answers conversational queries without web search."

    async def run(self, context: AgentContext) -> AgentResult:
        messages: list[LLMMessage] = []

        # Include conversation history from context
        for msg in context.conversation_history:
            messages.append(
                LLMMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                )
            )

        messages.append(LLMMessage(role="user", content=context.user_message))

        request = LLMRequest(
            messages=messages,
            model=self._model,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.7,
        )

        response = await self._llm.generate(request)

        return AgentResult(
            agent_name=self.name,
            response=response.content,
            token_usage=response.usage,
        )
