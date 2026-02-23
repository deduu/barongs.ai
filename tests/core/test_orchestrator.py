"""Tests for orchestrator engine and all strategies."""

from __future__ import annotations

import asyncio

import pytest

from src.core.interfaces.agent import Agent
from src.core.interfaces.orchestrator import Orchestrator
from src.core.models.results import AgentResult
from src.core.orchestrator.strategies.parallel import ParallelStrategy
from src.core.orchestrator.strategies.pipeline import PipelineStrategy
from src.core.orchestrator.strategies.router import RouterStrategy
from src.core.orchestrator.strategies.single_agent import SingleAgentStrategy


class TestSingleAgentStrategy:
    async def test_runs_first_agent(self, stub_agent, agent_context):
        strategy = SingleAgentStrategy()
        orch = Orchestrator(strategy=strategy, agents=[stub_agent])
        result = await orch.run(agent_context)
        assert result.agent_name == "stub_agent"
        assert "Hello, world!" in result.response

    async def test_raises_on_empty_agents(self, agent_context):
        strategy = SingleAgentStrategy()
        orch = Orchestrator(strategy=strategy, agents=[])
        with pytest.raises(ValueError):
            await orch.run(agent_context)


class TestPipelineStrategy:
    async def test_chains_agents(self, stub_agent, agent_context):
        strategy = PipelineStrategy()
        orch = Orchestrator(strategy=strategy, agents=[stub_agent, stub_agent])
        result = await orch.run(agent_context)
        # Second agent receives first agent's output "Echo: Hello, world!"
        # So second agent's response is "Echo: Echo: Hello, world!"
        assert "Echo: Echo:" in result.response

    async def test_raises_on_empty_agents(self, agent_context):
        strategy = PipelineStrategy()
        orch = Orchestrator(strategy=strategy, agents=[])
        with pytest.raises(ValueError):
            await orch.run(agent_context)


class TestParallelStrategy:
    async def test_runs_all_agents(self, stub_agent, agent_context):
        strategy = ParallelStrategy()
        orch = Orchestrator(strategy=strategy, agents=[stub_agent, stub_agent])
        result = await orch.run(agent_context)
        assert result.agent_name == "parallel_aggregate"
        assert result.metadata.get("sources") == ["stub_agent", "stub_agent"]

    async def test_custom_merge(self, stub_agent, agent_context):
        def custom_merge(results):
            return AgentResult(
                agent_name="custom",
                response=f"Got {len(results)} results",
            )

        strategy = ParallelStrategy(merge_fn=custom_merge)
        orch = Orchestrator(strategy=strategy, agents=[stub_agent, stub_agent])
        result = await orch.run(agent_context)
        assert result.response == "Got 2 results"

    async def test_raises_on_empty_agents(self, agent_context):
        strategy = ParallelStrategy()
        orch = Orchestrator(strategy=strategy, agents=[])
        result = await orch.run(agent_context)
        # Empty parallel should produce an empty aggregate
        assert result.agent_name == "parallel_aggregate"


class TestRouterStrategy:
    async def test_selects_agent(self, stub_agent, agent_context):
        async def always_first(agents, ctx):
            return agents[0]

        strategy = RouterStrategy(routing_fn=always_first)
        orch = Orchestrator(strategy=strategy, agents=[stub_agent])
        result = await orch.run(agent_context)
        assert result.agent_name == "stub_agent"


class TestOrchestratorTimeout:
    async def test_timeout_raises(self, agent_context):
        class SlowAgent(Agent):
            @property
            def name(self):
                return "slow"

            async def run(self, context):
                await asyncio.sleep(10)
                return AgentResult(agent_name="slow", response="done")

        strategy = SingleAgentStrategy()
        orch = Orchestrator(strategy=strategy, agents=[SlowAgent()], timeout_seconds=0.1)
        with pytest.raises(asyncio.TimeoutError):
            await orch.run(agent_context)


class TestOrchestratorStrategySwap:
    async def test_swap_strategy(self, stub_agent, agent_context):
        orch = Orchestrator(
            strategy=SingleAgentStrategy(),
            agents=[stub_agent],
        )
        result1 = await orch.run(agent_context)
        assert result1.agent_name == "stub_agent"

        orch.strategy = ParallelStrategy()
        result2 = await orch.run(agent_context)
        assert result2.agent_name == "parallel_aggregate"
