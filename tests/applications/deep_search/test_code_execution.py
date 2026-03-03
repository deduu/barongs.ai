from __future__ import annotations

from unittest.mock import AsyncMock, patch

from src.applications.deep_search.tools.code_execution import CodeExecutionTool
from src.core.models.context import ToolInput


class TestCodeExecutionToolProperties:
    def test_name(self):
        tool = CodeExecutionTool()
        assert tool.name == "code_execution"

    def test_description(self):
        tool = CodeExecutionTool()
        assert "code" in tool.description.lower() or "execute" in tool.description.lower()

    def test_input_schema(self):
        tool = CodeExecutionTool()
        assert "code" in tool.input_schema["properties"]


class TestCodeExecutionToolExecution:
    @patch("src.applications.deep_search.tools.code_execution.aiodocker")
    async def test_successful_execution(self, mock_aiodocker):
        mock_container = AsyncMock()
        mock_container.wait = AsyncMock(return_value={"StatusCode": 0})
        mock_container.log = AsyncMock(return_value=["Hello World\n"])
        mock_container.delete = AsyncMock()

        mock_docker = AsyncMock()
        mock_docker.containers.create_or_replace = AsyncMock(return_value=mock_container)
        mock_docker.close = AsyncMock()
        mock_aiodocker.Docker.return_value = mock_docker

        tool = CodeExecutionTool()
        tool_input = ToolInput(
            tool_name="code_execution",
            parameters={"code": "print('Hello World')"},
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        assert result.output["exit_code"] == 0
        assert "Hello World" in result.output["stdout"]

    @patch("src.applications.deep_search.tools.code_execution.aiodocker")
    async def test_execution_with_error(self, mock_aiodocker):
        mock_container = AsyncMock()
        mock_container.wait = AsyncMock(return_value={"StatusCode": 1})
        mock_container.log = AsyncMock(side_effect=[
            [],  # stdout
            ["NameError: name 'x' is not defined\n"],  # stderr
        ])
        mock_container.delete = AsyncMock()

        mock_docker = AsyncMock()
        mock_docker.containers.create_or_replace = AsyncMock(return_value=mock_container)
        mock_docker.close = AsyncMock()
        mock_aiodocker.Docker.return_value = mock_docker

        tool = CodeExecutionTool()
        tool_input = ToolInput(
            tool_name="code_execution",
            parameters={"code": "print(x)"},
        )
        result = await tool.execute(tool_input)

        assert result.success is True  # Tool succeeded, code had error
        assert result.output["exit_code"] == 1

    @patch("src.applications.deep_search.tools.code_execution.aiodocker")
    async def test_docker_failure(self, mock_aiodocker):
        mock_docker = AsyncMock()
        mock_docker.containers.create_or_replace = AsyncMock(
            side_effect=Exception("Docker daemon not running")
        )
        mock_docker.close = AsyncMock()
        mock_aiodocker.Docker.return_value = mock_docker

        tool = CodeExecutionTool()
        tool_input = ToolInput(
            tool_name="code_execution",
            parameters={"code": "print('test')"},
        )
        result = await tool.execute(tool_input)

        assert result.success is False
        assert result.error is not None

    @patch("src.applications.deep_search.tools.code_execution.aiodocker")
    async def test_timeout_enforcement(self, mock_aiodocker):
        """Test that execution has a timeout."""
        import asyncio

        mock_container = AsyncMock()
        mock_container.wait = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_container.kill = AsyncMock()
        mock_container.delete = AsyncMock()

        mock_docker = AsyncMock()
        mock_docker.containers.create_or_replace = AsyncMock(return_value=mock_container)
        mock_docker.close = AsyncMock()
        mock_aiodocker.Docker.return_value = mock_docker

        tool = CodeExecutionTool(timeout_seconds=1)
        tool_input = ToolInput(
            tool_name="code_execution",
            parameters={"code": "import time; time.sleep(100)"},
        )
        result = await tool.execute(tool_input)

        assert result.success is False
        assert "timeout" in result.error.lower()
