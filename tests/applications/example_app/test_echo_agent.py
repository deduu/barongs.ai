"""Tests for the EchoAgent — TDD: written before implementation."""

from __future__ import annotations

from src.applications.example_app.agents.echo_agent import EchoAgent
from src.core.models.context import AgentContext


class TestEchoAgent:
    async def test_echoes_user_message(self):
        agent = EchoAgent()
        ctx = AgentContext(user_message="Hello!")
        result = await agent.run(ctx)
        assert "Hello!" in result.response

    async def test_agent_name(self):
        agent = EchoAgent()
        assert agent.name == "echo_agent"

    async def test_has_description(self):
        agent = EchoAgent()
        assert len(agent.description) > 0

    async def test_result_metadata(self):
        agent = EchoAgent()
        ctx = AgentContext(user_message="test")
        result = await agent.run(ctx)
        assert result.agent_name == "echo_agent"
