from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.core.interfaces.orchestrator import Orchestrator
from src.core.middleware.auth import create_api_key_dependency
from src.core.models.config import AppSettings
from src.core.models.context import AgentContext


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    agent_name: str
    metadata: dict[str, object] = {}


def create_router(orchestrator: Orchestrator, settings: AppSettings) -> APIRouter:
    """Create the example app router with auth dependency."""
    router = APIRouter(prefix="/api", tags=["chat"])
    verify_key = create_api_key_dependency(settings)

    @router.post("/chat", response_model=ChatResponse)
    async def chat(
        request: ChatRequest,
        _api_key: str = Depends(verify_key),
    ) -> ChatResponse:
        context = AgentContext(user_message=request.message)
        result = await orchestrator.run(context)
        return ChatResponse(
            response=result.response,
            agent_name=result.agent_name,
            metadata=result.metadata,
        )

    return router
