from __future__ import annotations

from typing import Any

import networkx as nx

from src.core.interfaces.tool import Tool
from src.core.models.context import ToolInput
from src.core.models.results import ToolResult


class KnowledgeGraphTool(Tool):
    """In-memory knowledge graph using NetworkX."""

    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()

    @property
    def name(self) -> str:
        return "knowledge_graph"

    @property
    def description(self) -> str:
        return "Manage an in-memory knowledge graph: add entities, relationships, and query connections."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add_entity", "add_relationship", "query_connections", "get_summary"],
                    "description": "Operation to perform on the knowledge graph",
                },
                "entity_id": {"type": "string"},
                "entity_type": {"type": "string"},
                "properties": {"type": "object"},
                "source_id": {"type": "string"},
                "target_id": {"type": "string"},
                "relationship": {"type": "string"},
            },
            "required": ["operation"],
        }

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        operation = tool_input.parameters.get("operation")

        if operation == "add_entity":
            return self._add_entity(tool_input.parameters)
        elif operation == "add_relationship":
            return self._add_relationship(tool_input.parameters)
        elif operation == "query_connections":
            return self._query_connections(tool_input.parameters)
        elif operation == "get_summary":
            return self._get_summary()
        else:
            return ToolResult(
                tool_name=self.name,
                output=None,
                success=False,
                error=f"Unknown operation: {operation}",
            )

    def _add_entity(self, params: dict[str, Any]) -> ToolResult:
        entity_id = params.get("entity_id", "")
        entity_type = params.get("entity_type", "")
        properties = params.get("properties", {})

        self._graph.add_node(
            entity_id,
            entity_type=entity_type,
            **properties,
        )
        return ToolResult(
            tool_name=self.name,
            output={"entity_id": entity_id, "entity_type": entity_type},
        )

    def _add_relationship(self, params: dict[str, Any]) -> ToolResult:
        source_id = params.get("source_id", "")
        target_id = params.get("target_id", "")
        relationship = params.get("relationship", "")

        self._graph.add_edge(source_id, target_id, relationship=relationship)
        return ToolResult(
            tool_name=self.name,
            output={
                "source_id": source_id,
                "target_id": target_id,
                "relationship": relationship,
            },
        )

    def _query_connections(self, params: dict[str, Any]) -> ToolResult:
        entity_id = params.get("entity_id", "")

        if entity_id not in self._graph:
            return ToolResult(
                tool_name=self.name,
                output={"connections": []},
            )

        connections: list[dict[str, Any]] = []

        # Outgoing edges
        for _, target, data in self._graph.out_edges(entity_id, data=True):
            connections.append({
                "direction": "outgoing",
                "entity_id": target,
                "relationship": data.get("relationship", ""),
            })

        # Incoming edges
        for source, _, data in self._graph.in_edges(entity_id, data=True):
            connections.append({
                "direction": "incoming",
                "entity_id": source,
                "relationship": data.get("relationship", ""),
            })

        return ToolResult(
            tool_name=self.name,
            output={"connections": connections},
        )

    def _get_summary(self) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            output={
                "node_count": self._graph.number_of_nodes(),
                "edge_count": self._graph.number_of_edges(),
                "nodes": list(self._graph.nodes()),
            },
        )
