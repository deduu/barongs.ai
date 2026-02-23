from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.core.models.context import ToolInput
from src.core.models.results import ToolResult


class Tool(ABC):
    """Base class for all tools.

    Tools are stateless functions with schema-validated inputs.
    They are invoked by agents via the orchestrator.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """What this tool does, used for agent tool-selection."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema for the tool's input parameters."""
        ...

    @abstractmethod
    async def execute(self, tool_input: ToolInput) -> ToolResult:
        """Run the tool.

        Args:
            tool_input: Validated input conforming to input_schema.

        Returns:
            ToolResult with output data and metadata.
        """
        ...

    async def validate_input(self, raw: dict[str, Any]) -> ToolInput:
        """Hook to perform custom validation beyond JSON Schema."""
        return ToolInput(tool_name=self.name, parameters=raw)
