from __future__ import annotations

import json
from unittest.mock import AsyncMock

from src.applications.deep_search.agents.research_planner import ResearchPlannerAgent
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext


class TestResearchPlannerAgent:
    def test_name(self):
        llm = AsyncMock()
        agent = ResearchPlannerAgent(llm_provider=llm, model="test-model")
        assert agent.name == "research_planner"

    async def test_produces_research_plan(self):
        plan_json = json.dumps({
            "tasks": [
                {
                    "task_id": "t1",
                    "query": "What is Python GIL?",
                    "task_type": "secondary_web",
                    "depends_on": [],
                    "agent_name": "deep_web_researcher",
                },
                {
                    "task_id": "t2",
                    "query": "Verify Python GIL claims",
                    "task_type": "fact_check",
                    "depends_on": ["t1"],
                    "agent_name": "fact_checker",
                },
            ]
        })

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content=plan_json, model="test-model", usage={"total_tokens": 100},
        ))

        agent = ResearchPlannerAgent(llm_provider=llm, model="test-model")
        context = AgentContext(user_message="How does Python GIL work?")
        result = await agent.run(context)

        assert result.agent_name == "research_planner"
        assert "research_plan" in result.metadata
        plan = result.metadata["research_plan"]
        assert len(plan["tasks"]) == 2
        assert plan["tasks"][0]["task_id"] == "t1"

    async def test_handles_llm_json_in_markdown_block(self):
        """LLM may wrap JSON in ```json``` blocks."""
        plan_json = json.dumps({
            "tasks": [
                {
                    "task_id": "t1",
                    "query": "test",
                    "task_type": "secondary_web",
                    "depends_on": [],
                    "agent_name": "deep_web_researcher",
                },
            ]
        })

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content=f"```json\n{plan_json}\n```", model="test-model",
        ))

        agent = ResearchPlannerAgent(llm_provider=llm, model="test-model")
        context = AgentContext(user_message="test query")
        result = await agent.run(context)

        assert "research_plan" in result.metadata
        assert len(result.metadata["research_plan"]["tasks"]) == 1

    async def test_includes_entity_context_in_prompt(self):
        plan_json = json.dumps({
            "tasks": [{"task_id": "t1", "query": "test", "task_type": "secondary_web", "depends_on": [], "agent_name": "deep_web_researcher"}],
        })
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(content=plan_json, model="test"))

        agent = ResearchPlannerAgent(llm_provider=llm, model="test")
        context = AgentContext(
            user_message="What is Auditi?",
            metadata={"entity_grounding": {
                "name": "Auditi",
                "description": "A Python CLI for GitHub auditing",
                "key_attributes": ["GitHub", "CLI"],
            }},
        )
        await agent.run(context)

        call_args = llm.generate.call_args[0][0]
        assert "TARGET ENTITY" in call_args.system_prompt
        assert "Auditi" in call_args.system_prompt

    async def test_plan_preserves_entity_grounding(self):
        plan_json = json.dumps({
            "tasks": [{"task_id": "t1", "query": "test", "task_type": "secondary_web", "depends_on": [], "agent_name": "deep_web_researcher"}],
        })
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(content=plan_json, model="test"))

        entity = {"name": "Auditi", "description": "A tool", "key_attributes": []}
        agent = ResearchPlannerAgent(llm_provider=llm, model="test")
        context = AgentContext(user_message="test", metadata={"entity_grounding": entity})
        result = await agent.run(context)

        assert result.metadata["research_plan"]["entity_grounding"] == entity

    async def test_works_without_entity_grounding(self):
        plan_json = json.dumps({
            "tasks": [{"task_id": "t1", "query": "test", "task_type": "secondary_web", "depends_on": [], "agent_name": "deep_web_researcher"}],
        })
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(content=plan_json, model="test"))

        agent = ResearchPlannerAgent(llm_provider=llm, model="test")
        context = AgentContext(user_message="test")
        result = await agent.run(context)

        assert "research_plan" in result.metadata

    async def test_llm_failure_returns_error(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(side_effect=Exception("LLM down"))

        agent = ResearchPlannerAgent(llm_provider=llm, model="test-model")
        context = AgentContext(user_message="test")
        result = await agent.run(context)

        assert "error" in result.response.lower() or "error" in result.metadata
