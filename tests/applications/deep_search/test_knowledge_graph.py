from __future__ import annotations

from src.applications.deep_search.tools.knowledge_graph import KnowledgeGraphTool
from src.core.models.context import ToolInput


class TestKnowledgeGraphToolProperties:
    def test_name(self):
        tool = KnowledgeGraphTool()
        assert tool.name == "knowledge_graph"

    def test_description(self):
        tool = KnowledgeGraphTool()
        assert "knowledge" in tool.description.lower() or "graph" in tool.description.lower()

    def test_input_schema(self):
        tool = KnowledgeGraphTool()
        assert "operation" in tool.input_schema["properties"]


class TestKnowledgeGraphToolAddEntity:
    async def test_add_entity(self):
        tool = KnowledgeGraphTool()
        tool_input = ToolInput(
            tool_name="knowledge_graph",
            parameters={
                "operation": "add_entity",
                "entity_id": "python",
                "entity_type": "language",
                "properties": {"name": "Python", "year": 1991},
            },
        )
        result = await tool.execute(tool_input)

        assert result.success is True
        assert result.output["entity_id"] == "python"

    async def test_add_duplicate_entity_updates(self):
        tool = KnowledgeGraphTool()
        inp1 = ToolInput(
            tool_name="knowledge_graph",
            parameters={
                "operation": "add_entity",
                "entity_id": "python",
                "entity_type": "language",
                "properties": {"name": "Python"},
            },
        )
        await tool.execute(inp1)

        inp2 = ToolInput(
            tool_name="knowledge_graph",
            parameters={
                "operation": "add_entity",
                "entity_id": "python",
                "entity_type": "language",
                "properties": {"name": "Python", "version": "3.11"},
            },
        )
        result = await tool.execute(inp2)
        assert result.success is True


class TestKnowledgeGraphToolAddRelationship:
    async def test_add_relationship(self):
        tool = KnowledgeGraphTool()
        # Add entities first
        for eid, etype in [("python", "language"), ("guido", "person")]:
            await tool.execute(ToolInput(
                tool_name="knowledge_graph",
                parameters={
                    "operation": "add_entity",
                    "entity_id": eid,
                    "entity_type": etype,
                },
            ))

        result = await tool.execute(ToolInput(
            tool_name="knowledge_graph",
            parameters={
                "operation": "add_relationship",
                "source_id": "guido",
                "target_id": "python",
                "relationship": "created",
            },
        ))

        assert result.success is True
        assert result.output["relationship"] == "created"


class TestKnowledgeGraphToolQueryConnections:
    async def test_query_connections(self):
        tool = KnowledgeGraphTool()
        # Build a small graph
        for eid, etype in [("a", "node"), ("b", "node"), ("c", "node")]:
            await tool.execute(ToolInput(
                tool_name="knowledge_graph",
                parameters={"operation": "add_entity", "entity_id": eid, "entity_type": etype},
            ))
        for src, tgt, rel in [("a", "b", "links"), ("b", "c", "links")]:
            await tool.execute(ToolInput(
                tool_name="knowledge_graph",
                parameters={
                    "operation": "add_relationship",
                    "source_id": src,
                    "target_id": tgt,
                    "relationship": rel,
                },
            ))

        result = await tool.execute(ToolInput(
            tool_name="knowledge_graph",
            parameters={"operation": "query_connections", "entity_id": "b"},
        ))

        assert result.success is True
        assert len(result.output["connections"]) >= 2


class TestKnowledgeGraphToolGetSummary:
    async def test_get_summary_empty(self):
        tool = KnowledgeGraphTool()
        result = await tool.execute(ToolInput(
            tool_name="knowledge_graph",
            parameters={"operation": "get_summary"},
        ))

        assert result.success is True
        assert result.output["node_count"] == 0
        assert result.output["edge_count"] == 0

    async def test_get_summary_with_data(self):
        tool = KnowledgeGraphTool()
        await tool.execute(ToolInput(
            tool_name="knowledge_graph",
            parameters={"operation": "add_entity", "entity_id": "a", "entity_type": "node"},
        ))
        await tool.execute(ToolInput(
            tool_name="knowledge_graph",
            parameters={"operation": "add_entity", "entity_id": "b", "entity_type": "node"},
        ))
        await tool.execute(ToolInput(
            tool_name="knowledge_graph",
            parameters={
                "operation": "add_relationship",
                "source_id": "a",
                "target_id": "b",
                "relationship": "links",
            },
        ))

        result = await tool.execute(ToolInput(
            tool_name="knowledge_graph",
            parameters={"operation": "get_summary"},
        ))

        assert result.output["node_count"] == 2
        assert result.output["edge_count"] == 1


class TestKnowledgeGraphToolInvalidOperation:
    async def test_invalid_operation(self):
        tool = KnowledgeGraphTool()
        result = await tool.execute(ToolInput(
            tool_name="knowledge_graph",
            parameters={"operation": "invalid_op"},
        ))

        assert result.success is False
