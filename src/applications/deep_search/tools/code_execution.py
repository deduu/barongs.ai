from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import Any

import aiodocker

from src.core.interfaces.tool import Tool
from src.core.middleware.circuit_breaker import CircuitBreaker
from src.core.models.context import ToolInput
from src.core.models.results import ToolResult

logger = logging.getLogger(__name__)


class CodeExecutionTool(Tool):
    """Execute Python code in an ephemeral Docker container."""

    def __init__(
        self,
        *,
        docker_image: str = "python:3.11-slim",
        memory_limit: str = "256m",
        timeout_seconds: int = 30,
        network_disabled: bool = True,
    ) -> None:
        self._docker_image = docker_image
        self._memory_limit = memory_limit
        self._timeout_seconds = timeout_seconds
        self._network_disabled = network_disabled
        self._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    @property
    def name(self) -> str:
        return "code_execution"

    @property
    def description(self) -> str:
        return "Execute Python code in a sandboxed Docker container."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
            },
            "required": ["code"],
        }

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        code = tool_input.parameters["code"]
        start_time = time.monotonic()

        docker: Any = None
        container: Any = None
        try:
            docker = aiodocker.Docker()

            config = {
                "Image": self._docker_image,
                "Cmd": ["python", "-c", code],
                "HostConfig": {
                    "Memory": self._parse_memory(self._memory_limit),
                    "NetworkMode": "none" if self._network_disabled else "bridge",
                },
            }

            container = await docker.containers.create_or_replace(
                config=config, name=f"barongsai-exec-{int(time.monotonic() * 1000)}",
            )
            await container.start()

            try:
                await asyncio.wait_for(
                    container.wait(), timeout=self._timeout_seconds
                )
            except TimeoutError:
                with contextlib.suppress(Exception):
                    await container.kill()
                await container.delete(force=True)
                await docker.close()
                elapsed = (time.monotonic() - start_time) * 1000
                return ToolResult(
                    tool_name=self.name,
                    output=None,
                    success=False,
                    error=f"Execution timeout after {self._timeout_seconds}s",
                    duration_ms=elapsed,
                )

            info = await container.wait()
            exit_code = info.get("StatusCode", -1)

            stdout_logs = await container.log(stdout=True)
            stderr_logs = await container.log(stderr=True)

            stdout = "".join(stdout_logs) if stdout_logs else ""
            stderr = "".join(stderr_logs) if stderr_logs else ""

            elapsed = (time.monotonic() - start_time) * 1000

            await container.delete(force=True)
            await docker.close()

            return ToolResult(
                tool_name=self.name,
                output={
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": exit_code,
                    "execution_time_ms": round(elapsed),
                },
                duration_ms=elapsed,
            )
        except TimeoutError:
            elapsed = (time.monotonic() - start_time) * 1000
            if container:
                try:
                    await container.kill()
                    await container.delete(force=True)
                except Exception:
                    pass
            if docker:
                await docker.close()
            return ToolResult(
                tool_name=self.name,
                output=None,
                success=False,
                error=f"Execution timeout after {self._timeout_seconds}s",
                duration_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start_time) * 1000
            if docker:
                with contextlib.suppress(Exception):
                    await docker.close()
            return ToolResult(
                tool_name=self.name,
                output=None,
                success=False,
                error=str(exc),
                duration_ms=elapsed,
            )

    @staticmethod
    def _parse_memory(mem_str: str) -> int:
        """Parse memory string like '256m' to bytes."""
        mem_str = mem_str.strip().lower()
        if mem_str.endswith("g"):
            return int(float(mem_str[:-1]) * 1024 * 1024 * 1024)
        if mem_str.endswith("m"):
            return int(float(mem_str[:-1]) * 1024 * 1024)
        if mem_str.endswith("k"):
            return int(float(mem_str[:-1]) * 1024)
        return int(mem_str)
