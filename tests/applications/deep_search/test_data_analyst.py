from __future__ import annotations

from unittest.mock import AsyncMock

from src.applications.deep_search.agents.data_analyst import DataAnalystAgent
from src.core.llm.models import LLMResponse
from src.core.models.context import AgentContext
from src.core.models.results import ToolResult


class TestDataAnalystAgent:
    def test_name(self):
        agent = DataAnalystAgent(
            llm_provider=AsyncMock(),
            code_execution_tool=AsyncMock(),
        )
        assert agent.name == "data_analyst"

    async def test_generates_and_executes_code(self):
        llm = AsyncMock()
        # First call: generate code
        # Second call: interpret results
        llm.generate = AsyncMock(side_effect=[
            LLMResponse(content="print(42)", model="test"),
            LLMResponse(content="The result is 42.", model="test", usage={"total_tokens": 50}),
        ])

        code_tool = AsyncMock()
        code_tool.name = "code_execution"
        code_tool.execute = AsyncMock(return_value=ToolResult(
            tool_name="code_execution",
            output={"stdout": "42\n", "stderr": "", "exit_code": 0, "execution_time_ms": 100},
        ))

        agent = DataAnalystAgent(llm_provider=llm, code_execution_tool=code_tool)
        context = AgentContext(user_message="Calculate 6 * 7")
        result = await agent.run(context)

        assert result.agent_name == "data_analyst"
        assert "findings" in result.metadata
        assert code_tool.execute.called

    async def test_code_error_triggers_retry(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(side_effect=[
            LLMResponse(content="print(x)", model="test"),  # buggy code
            LLMResponse(content="print(42)", model="test"),  # fixed code
            LLMResponse(content="The answer is 42.", model="test", usage={"total_tokens": 50}),
        ])

        code_tool = AsyncMock()
        code_tool.name = "code_execution"
        code_tool.execute = AsyncMock(side_effect=[
            ToolResult(
                tool_name="code_execution",
                output={"stdout": "", "stderr": "NameError: name 'x' is not defined", "exit_code": 1, "execution_time_ms": 50},
            ),
            ToolResult(
                tool_name="code_execution",
                output={"stdout": "42\n", "stderr": "", "exit_code": 0, "execution_time_ms": 50},
            ),
        ])

        agent = DataAnalystAgent(llm_provider=llm, code_execution_tool=code_tool)
        context = AgentContext(user_message="Calculate something")
        await agent.run(context)

        assert code_tool.execute.call_count == 2
