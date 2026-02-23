from __future__ import annotations

from fastapi import FastAPI

from src.applications.example_app.agents.echo_agent import EchoAgent
from src.applications.example_app.config import ExampleAppSettings
from src.applications.example_app.routes import create_router
from src.core.interfaces.orchestrator import Orchestrator
from src.core.orchestrator.strategies.single_agent import SingleAgentStrategy
from src.core.server.factory import create_app


def create_example_app() -> FastAPI:
    """Composition root: wire agents, tools, memory, orchestrator, and routes."""
    settings = ExampleAppSettings()

    # Create agents
    echo_agent = EchoAgent()

    # Wire orchestrator with strategy
    orchestrator = Orchestrator(
        strategy=SingleAgentStrategy(),
        agents=[echo_agent],
        timeout_seconds=settings.agent_timeout_seconds,
    )

    # Create FastAPI app and mount routes
    app = create_app(settings)
    router = create_router(orchestrator, settings)
    app.include_router(router)

    return app


# For `uvicorn src.applications.example_app.main:app`
app = create_example_app()

if __name__ == "__main__":
    import uvicorn

    settings = ExampleAppSettings()
    uvicorn.run(
        "src.applications.example_app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
