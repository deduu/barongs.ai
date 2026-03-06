from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.middleware.logging import setup_logging
from src.core.middleware.rate_limit_middleware import RateLimitMiddleware
from src.core.models.config import AppSettings
from src.core.server.diagnostics import create_diagnostics_router
from src.core.server.exception_handlers import (
    GlobalExceptionMiddleware,
    register_exception_handlers,
)
from src.core.server.health import router as health_router

LifecycleHook = Callable[[], Awaitable[None]]


def create_app(
    settings: AppSettings | None = None,
    *,
    on_startup: list[LifecycleHook] | None = None,
    on_shutdown: list[LifecycleHook] | None = None,
    rate_limiter: Any | None = None,
) -> FastAPI:
    """Application factory. Creates a configured FastAPI instance.

    Serving layer is separate from business logic. Agents, tools, and
    orchestrator are wired in by the specific application, not by this factory.

    Args:
        settings: Application settings.
        on_startup: Optional async callables invoked during application startup.
        on_shutdown: Optional async callables invoked during application shutdown.
        rate_limiter: Optional pre-configured rate limiter (e.g. RedisRateLimiter
            for distributed deployments). Falls back to in-memory limiter.
    """
    settings = settings or AppSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        app.state.settings = settings
        app.state.shutting_down = False
        setup_logging(
            log_level=settings.log_level,
            json_format=settings.environment == "production",
        )
        for hook in on_startup or []:
            await hook()
        yield
        app.state.shutting_down = True
        # Brief drain period so load balancer stops sending traffic
        await asyncio.sleep(2)
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

    app.add_middleware(GlobalExceptionMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        max_tokens=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
        limiter=rate_limiter,
    )
    register_exception_handlers(app)
    app.include_router(health_router)

    if settings.environment != "production":
        app.include_router(create_diagnostics_router())

    return app
