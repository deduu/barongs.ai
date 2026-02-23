"""Tests for core ABCs — verify they cannot be instantiated directly
and that stub implementations work correctly."""

from __future__ import annotations

import pytest

from src.core.interfaces.agent import Agent
from src.core.interfaces.memory import Memory
from src.core.interfaces.tool import Tool
from src.core.models.context import ToolInput


class TestAgentABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            Agent()  # type: ignore[abstract]

    async def test_stub_agent_runs(self, stub_agent, agent_context):
        result = await stub_agent.run(agent_context)
        assert result.agent_name == "stub_agent"
        assert "Hello, world!" in result.response

    async def test_stub_agent_has_name(self, stub_agent):
        assert stub_agent.name == "stub_agent"

    async def test_default_description_is_empty(self, stub_agent):
        assert stub_agent.description == ""

    async def test_setup_and_teardown_are_noop(self, stub_agent):
        await stub_agent.setup()
        await stub_agent.teardown()


class TestToolABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            Tool()  # type: ignore[abstract]

    async def test_stub_tool_executes(self, stub_tool):
        tool_input = ToolInput(tool_name="stub_tool", parameters={"query": "test"})
        result = await stub_tool.execute(tool_input)
        assert result.tool_name == "stub_tool"
        assert result.output == "stub_output"
        assert result.success is True

    async def test_stub_tool_has_schema(self, stub_tool):
        schema = stub_tool.input_schema
        assert schema["type"] == "object"
        assert "query" in schema["properties"]

    async def test_validate_input_returns_tool_input(self, stub_tool):
        result = await stub_tool.validate_input({"query": "test"})
        assert isinstance(result, ToolInput)
        assert result.tool_name == "stub_tool"


class TestMemoryABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            Memory()  # type: ignore[abstract]

    async def test_stub_memory_get_set(self, stub_memory):
        await stub_memory.set("key1", "value1")
        result = await stub_memory.get("key1")
        assert result == "value1"

    async def test_stub_memory_get_missing(self, stub_memory):
        result = await stub_memory.get("nonexistent")
        assert result is None

    async def test_stub_memory_delete(self, stub_memory):
        await stub_memory.set("key1", "value1")
        deleted = await stub_memory.delete("key1")
        assert deleted is True
        assert await stub_memory.get("key1") is None

    async def test_stub_memory_delete_missing(self, stub_memory):
        deleted = await stub_memory.delete("nonexistent")
        assert deleted is False

    async def test_stub_memory_search(self, stub_memory):
        await stub_memory.set("greeting", "hello world")
        await stub_memory.set("farewell", "goodbye")
        results = await stub_memory.search("hello")
        assert len(results) == 1
        assert results[0]["key"] == "greeting"

    async def test_stub_memory_clear_raises(self, stub_memory):
        with pytest.raises(NotImplementedError):
            await stub_memory.clear()
