"""Tests for PipelineWithMetadataStrategy."""

from __future__ import annotations

from typing import Any

import pytest

from src.core.interfaces.agent import Agent
from src.core.interfaces.orchestrator import Orchestrator
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult
from src.core.orchestrator.strategies.pipeline_metadata import (
    PipelineWithMetadataStrategy,
)


class MetadataAgent(Agent):
    """Agent that reads from and writes to context metadata."""

    def __init__(
        self, agent_name: str, read_key: str | None, write_key: str, write_value: Any
    ) -> None:
        self._name = agent_name
        self._read_key = read_key
        self._write_key = write_key
        self._write_value = write_value

    @property
    def name(self) -> str:
        return self._name

    async def run(self, context: AgentContext) -> AgentResult:
        read_val = context.metadata.get(self._read_key) if self._read_key else None
        response = f"read={read_val}" if read_val else "no_read"
        return AgentResult(
            agent_name=self.name,
            response=response,
            metadata={self._write_key: self._write_value},
        )


class TestPipelineWithMetadataStrategy:
    async def test_propagates_metadata_between_agents(self, agent_context: AgentContext) -> None:
        """Each agent's metadata output should be available to the next agent."""
        agent_a = MetadataAgent(
            "agent_a", read_key=None, write_key="requirements", write_value={"app": "todo"}
        )
        agent_b = MetadataAgent(
            "agent_b",
            read_key="requirements",
            write_key="appspec",
            write_value={"models": ["Task"]},
        )

        strategy = PipelineWithMetadataStrategy()
        orch = Orchestrator(strategy=strategy, agents=[agent_a, agent_b])
        result = await orch.run(agent_context)

        # Agent B should have read agent A's metadata
        assert "read={'app': 'todo'}" in result.response
        # Final result should contain merged metadata from both agents
        assert result.metadata["requirements"] == {"app": "todo"}
        assert result.metadata["appspec"] == {"models": ["Task"]}

    async def test_preserves_initial_context_metadata(self, agent_context: AgentContext) -> None:
        """Metadata from the initial context should survive through the pipeline."""
        ctx = agent_context.model_copy(update={"metadata": {"job_id": "test-123"}})
        agent = MetadataAgent("agent_a", read_key="job_id", write_key="output", write_value="done")

        strategy = PipelineWithMetadataStrategy()
        orch = Orchestrator(strategy=strategy, agents=[agent])
        result = await orch.run(ctx)

        assert "read=test-123" in result.response
        assert result.metadata["job_id"] == "test-123"
        assert result.metadata["output"] == "done"

    async def test_later_agents_override_earlier_metadata_keys(self) -> None:
        """If two agents write the same metadata key, the later one wins."""
        ctx = AgentContext(user_message="test")
        agent_a = MetadataAgent("agent_a", read_key=None, write_key="status", write_value="draft")
        agent_b = MetadataAgent(
            "agent_b", read_key="status", write_key="status", write_value="final"
        )

        strategy = PipelineWithMetadataStrategy()
        orch = Orchestrator(strategy=strategy, agents=[agent_a, agent_b])
        result = await orch.run(ctx)

        assert result.metadata["status"] == "final"

    async def test_chains_response_as_user_message(self, agent_context: AgentContext) -> None:
        """Like PipelineStrategy, response should become the next agent's user_message."""

        class EchoAgent(Agent):
            @property
            def name(self) -> str:
                return "echo"

            async def run(self, context: AgentContext) -> AgentResult:
                return AgentResult(
                    agent_name=self.name,
                    response=f"Echo: {context.user_message}",
                )

        strategy = PipelineWithMetadataStrategy()
        orch = Orchestrator(strategy=strategy, agents=[EchoAgent(), EchoAgent()])
        result = await orch.run(agent_context)

        assert "Echo: Echo:" in result.response

    async def test_raises_on_empty_agents(self, agent_context: AgentContext) -> None:
        strategy = PipelineWithMetadataStrategy()
        orch = Orchestrator(strategy=strategy, agents=[])
        with pytest.raises(ValueError):
            await orch.run(agent_context)

    async def test_single_agent_returns_its_result(self, agent_context: AgentContext) -> None:
        agent = MetadataAgent("solo", read_key=None, write_key="result", write_value="ok")

        strategy = PipelineWithMetadataStrategy()
        orch = Orchestrator(strategy=strategy, agents=[agent])
        result = await orch.run(agent_context)

        assert result.agent_name == "solo"
        assert result.metadata["result"] == "ok"

    async def test_three_stage_pipeline_accumulates_metadata(self) -> None:
        """Simulate a mini generation pipeline: parse → generate → validate."""
        ctx = AgentContext(user_message="build a todo app", metadata={"job_id": "j1"})

        parse_agent = MetadataAgent(
            "parse", read_key=None, write_key="requirements", write_value={"entities": ["Task"]}
        )
        gen_agent = MetadataAgent(
            "generate",
            read_key="requirements",
            write_key="files",
            write_value=["models.py", "routes.py"],
        )
        validate_agent = MetadataAgent(
            "validate", read_key="files", write_key="valid", write_value=True
        )

        strategy = PipelineWithMetadataStrategy()
        orch = Orchestrator(strategy=strategy, agents=[parse_agent, gen_agent, validate_agent])
        result = await orch.run(ctx)

        assert result.metadata["job_id"] == "j1"
        assert result.metadata["requirements"] == {"entities": ["Task"]}
        assert result.metadata["files"] == ["models.py", "routes.py"]
        assert result.metadata["valid"] is True
