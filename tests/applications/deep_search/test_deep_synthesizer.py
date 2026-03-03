from __future__ import annotations

from unittest.mock import AsyncMock

from src.applications.deep_search.agents.deep_synthesizer import DeepSynthesizerAgent
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext


class TestDeepSynthesizerAgent:
    def test_name(self):
        agent = DeepSynthesizerAgent(llm_provider=AsyncMock())
        assert agent.name == "deep_synthesizer"

    async def test_produces_research_report(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content="# Executive Summary\nPython's GIL is...\n\n## Section 1\nDetails...",
            model="test",
            usage={"total_tokens": 200},
        ))

        agent = DeepSynthesizerAgent(llm_provider=llm)
        findings = [
            {"finding_id": "f1", "content": "Python uses GIL", "source_url": "https://a.com", "confidence": 0.9},
            {"finding_id": "f2", "content": "GIL prevents true parallelism", "source_url": "https://b.com", "confidence": 0.85},
        ]
        context = AgentContext(
            user_message="How does Python GIL work?",
            metadata={"findings": findings},
        )
        result = await agent.run(context)

        assert result.agent_name == "deep_synthesizer"
        assert len(result.response) > 0
        assert result.token_usage.get("total_tokens", 0) > 0

    async def test_stream_run(self):
        llm = AsyncMock()

        async def mock_stream(*args, **kwargs):
            for token in ["Hello", " ", "World"]:
                yield token

        llm.stream = mock_stream

        agent = DeepSynthesizerAgent(llm_provider=llm)
        context = AgentContext(
            user_message="Summarize",
            metadata={"findings": []},
        )

        tokens = []
        async for token in agent.stream_run(context):
            tokens.append(token)

        assert tokens == ["Hello", " ", "World"]

    async def test_filters_misattributed_findings(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content="Report about Auditi CLI.", model="test", usage={"total_tokens": 100},
        ))

        agent = DeepSynthesizerAgent(llm_provider=llm)
        findings = [
            {"finding_id": "f1", "content": "Wrong entity finding", "source_url": "https://auditi.de", "confidence": 0.5},
            {"finding_id": "f2", "content": "Correct entity finding", "source_url": "https://github.com/deduu/auditi", "confidence": 0.9},
        ]
        context = AgentContext(
            user_message="What is Auditi?",
            metadata={
                "findings": findings,
                "misattributed_ids": ["f1"],
                "entity_grounding": {"name": "Auditi CLI", "description": "GitHub auditing CLI"},
            },
        )
        await agent.run(context)

        # The system prompt should only contain f2's content, not f1
        call_args = llm.generate.call_args[0][0]
        assert "Correct entity finding" in call_args.system_prompt
        assert "Wrong entity finding" not in call_args.system_prompt

    async def test_entity_context_in_synthesis_prompt(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(content="Report.", model="test", usage={"total_tokens": 50}))

        agent = DeepSynthesizerAgent(llm_provider=llm)
        context = AgentContext(
            user_message="test",
            metadata={
                "findings": [{"finding_id": "f1", "content": "test", "source_url": "https://a.com", "confidence": 0.8}],
                "entity_grounding": {"name": "TargetEntity", "description": "A specific entity", "source_urls": ["https://a.com"]},
            },
        )
        await agent.run(context)

        call_args = llm.generate.call_args[0][0]
        assert "TARGET ENTITY" in call_args.system_prompt
        assert "TargetEntity" in call_args.system_prompt

    async def test_low_relevance_guard_no_findings(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(content="No info found.", model="test", usage={"total_tokens": 30}))

        agent = DeepSynthesizerAgent(llm_provider=llm)
        context = AgentContext(user_message="test", metadata={"findings": []})
        await agent.run(context)

        call_args = llm.generate.call_args[0][0]
        assert "WARNING" in call_args.system_prompt
        assert "Do NOT fabricate" in call_args.system_prompt

    async def test_low_relevance_guard_all_filtered(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(content="No info.", model="test", usage={"total_tokens": 30}))

        agent = DeepSynthesizerAgent(llm_provider=llm)
        findings = [
            {"finding_id": "f1", "content": "Wrong", "source_url": "https://wrong.com", "confidence": 0.5},
        ]
        context = AgentContext(
            user_message="test",
            metadata={"findings": findings, "misattributed_ids": ["f1"]},
        )
        await agent.run(context)

        call_args = llm.generate.call_args[0][0]
        assert "WARNING" in call_args.system_prompt

    async def test_no_findings_still_produces_output(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content="No findings were available for this query.",
            model="test",
        ))

        agent = DeepSynthesizerAgent(llm_provider=llm)
        context = AgentContext(user_message="test", metadata={"findings": []})
        result = await agent.run(context)

        assert len(result.response) > 0
