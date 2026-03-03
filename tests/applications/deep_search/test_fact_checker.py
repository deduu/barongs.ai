from __future__ import annotations

import json
from unittest.mock import AsyncMock

from src.applications.deep_search.agents.fact_checker import FactCheckerAgent
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext


class TestFactCheckerAgent:
    def test_name(self):
        agent = FactCheckerAgent(llm_provider=AsyncMock())
        assert agent.name == "fact_checker"

    async def test_checks_findings_and_adjusts_confidence(self):
        findings = [
            {"finding_id": "f1", "content": "Python uses GIL", "confidence": 0.8, "source_url": "https://a.com"},
            {"finding_id": "f2", "content": "Python has no GIL", "confidence": 0.6, "source_url": "https://b.com"},
        ]

        fact_check_result = json.dumps({
            "checked_findings": [
                {"finding_id": "f1", "adjusted_confidence": 0.9, "notes": "Confirmed by multiple sources"},
                {"finding_id": "f2", "adjusted_confidence": 0.2, "notes": "Contradicted by official docs"},
            ],
            "contradictions": [
                {"finding_ids": ["f1", "f2"], "description": "Conflicting claims about GIL existence"},
            ],
        })

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content=fact_check_result, model="test", usage={"total_tokens": 100},
        ))

        agent = FactCheckerAgent(llm_provider=llm)
        context = AgentContext(
            user_message="Verify findings",
            metadata={"all_findings": [findings]},
        )
        result = await agent.run(context)

        assert result.agent_name == "fact_checker"
        assert "checked_findings" in result.metadata
        assert "contradictions" in result.metadata

    async def test_no_findings_returns_empty(self):
        llm = AsyncMock()
        agent = FactCheckerAgent(llm_provider=llm)
        context = AgentContext(
            user_message="Check facts",
            metadata={"all_findings": []},
        )
        result = await agent.run(context)

        assert result.metadata["checked_findings"] == []
        assert result.metadata["misattributed_ids"] == []

    async def test_detects_misattributed_findings(self):
        findings = [
            {"finding_id": "f1", "content": "Auditi.de is a German audit company", "source_url": "https://auditi.de"},
            {"finding_id": "f2", "content": "Auditi CLI audits GitHub repos", "source_url": "https://github.com/deduu/auditi"},
        ]

        fact_check_result = json.dumps({
            "checked_findings": [
                {"finding_id": "f1", "adjusted_confidence": 0.1, "notes": "Wrong entity", "entity_match": False},
                {"finding_id": "f2", "adjusted_confidence": 0.9, "notes": "Correct entity", "entity_match": True},
            ],
            "contradictions": [],
            "misattributions": [
                {"finding_id": "f1", "reason": "This finding is about auditi.de, not deduu/auditi"},
            ],
        })

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content=fact_check_result, model="test", usage={"total_tokens": 100},
        ))

        agent = FactCheckerAgent(llm_provider=llm)
        context = AgentContext(
            user_message="Verify findings",
            metadata={
                "all_findings": [findings],
                "entity_grounding": {"name": "Auditi CLI", "description": "GitHub auditing CLI by deduu"},
            },
        )
        result = await agent.run(context)

        assert "f1" in result.metadata["misattributed_ids"]
        assert "f2" not in result.metadata["misattributed_ids"]

    async def test_entity_context_in_prompt(self):
        findings = [{"finding_id": "f1", "content": "test", "source_url": "https://a.com"}]

        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content=json.dumps({"checked_findings": [], "contradictions": [], "misattributions": []}),
            model="test", usage={"total_tokens": 50},
        ))

        agent = FactCheckerAgent(llm_provider=llm)
        context = AgentContext(
            user_message="check",
            metadata={
                "all_findings": [findings],
                "entity_grounding": {"name": "TargetEntity", "description": "A specific entity"},
            },
        )
        await agent.run(context)

        call_args = llm.generate.call_args[0][0]
        assert "TARGET ENTITY" in call_args.system_prompt
        assert "TargetEntity" in call_args.system_prompt
