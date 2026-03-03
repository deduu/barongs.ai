from __future__ import annotations

import json
from unittest.mock import AsyncMock

from src.applications.deep_search.agents.reflection import ReflectionAgent
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext


class TestReflectionAgent:
    def test_name(self):
        agent = ReflectionAgent(llm_provider=AsyncMock())
        assert agent.name == "reflection"

    async def test_identifies_gaps_and_returns_new_tasks(self):
        reflection_result = json.dumps({
            "gaps": ["No data on Python 3.12 changes"],
            "new_tasks": [
                {
                    "task_id": "t_followup",
                    "query": "Python 3.12 GIL changes",
                    "task_type": "secondary_web",
                    "depends_on": [],
                    "agent_name": "deep_web_researcher",
                },
            ],
            "overall_confidence": 0.6,
        })

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content=reflection_result, model="test", usage={"total_tokens": 80},
        ))

        agent = ReflectionAgent(llm_provider=llm)
        findings = [{"finding_id": "f1", "content": "Python uses GIL", "confidence": 0.8}]
        context = AgentContext(
            user_message="Reflect on findings",
            metadata={"all_findings": [findings]},
        )
        result = await agent.run(context)

        assert result.agent_name == "reflection"
        assert "gaps" in result.metadata
        assert "new_tasks" in result.metadata
        assert len(result.metadata["new_tasks"]) == 1

    async def test_sufficient_findings_no_new_tasks(self):
        reflection_result = json.dumps({
            "gaps": [],
            "new_tasks": [],
            "overall_confidence": 0.9,
        })

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content=reflection_result, model="test",
        ))

        agent = ReflectionAgent(llm_provider=llm)
        context = AgentContext(
            user_message="Reflect",
            metadata={"all_findings": [[{"finding_id": "f1", "content": "test", "confidence": 0.9}]]},
        )
        result = await agent.run(context)

        assert result.metadata["new_tasks"] == []
        assert result.metadata["gaps"] == []
