from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.middleware.logging import setup_logging
from src.core.models.config import AppSettings
from src.core.server.exception_handlers import register_exception_handlers
from src.core.server.health import router as health_router

LifecycleHook = Callable[[], Awaitable[None]]


def create_app(
    settings: AppSettings | None = None,
    *,
    on_startup: list[LifecycleHook] | None = None,
    on_shutdown: list[LifecycleHook] | None = None,
) -> FastAPI:
    """Application factory. Creates a configured FastAPI instance.

    Serving layer is separate from business logic. Agents, tools, and
    orchestrator are wired in by the specific application, not by this factory.

    Args:
        settings: Application settings.
        on_startup: Optional async callables invoked during application startup.
        on_shutdown: Optional async callables invoked during application shutdown.
    """
    settings = settings or AppSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        app.state.settings = settings
        setup_logging(
            log_level=settings.log_level,
            json_format=settings.environment == "production",
        )
        for hook in on_startup or []:
            await hook()
        yield
        for hook in on_shutdown or []:
            await hook()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(health_router)

    return app
