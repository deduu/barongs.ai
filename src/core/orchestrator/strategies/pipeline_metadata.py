from __future__ import annotations

from src.core.interfaces.agent import Agent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult


class PipelineWithMetadataStrategy:
    """Run agents sequentially, propagating both response and metadata.

    Like PipelineStrategy, each agent's response becomes the next agent's
    user_message.  Additionally, each agent's result metadata is merged
    into the context metadata for subsequent agents, enabling structured
    data flow through a multi-stage pipeline.
    """

    async def execute(self, agents: list[Agent], context: AgentContext) -> AgentResult:
        if not agents:
            raise ValueError("PipelineWithMetadataStrategy requires at least one agent")

        current_context = context
        result: AgentResult | None = None

        for agent in agents:
            result = await agent.run(current_context)
            merged_metadata = {**current_context.metadata, **result.metadata}
            current_context = current_context.model_copy(
                update={"user_message": result.response, "metadata": merged_metadata},
            )

        assert result is not None
        # Merge all accumulated metadata into the final result
        final_metadata = {**current_context.metadata, **result.metadata}
        return result.model_copy(update={"metadata": final_metadata})
