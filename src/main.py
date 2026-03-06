"""Gateway composition root — serves both search_agent and deep_search.

Neither application imports the other. This gateway depends on both
and composes them into a single FastAPI instance.

Usage:
    uvicorn src.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.applications.deep_search.config import DeepSearchSettings
from src.applications.deep_search.main import wire_deep_search
from src.applications.search_agent.config import SearchAgentSettings
from src.applications.search_agent.main import create_search_app
from src.core.middleware.auth import create_api_key_dependency

logger = logging.getLogger(__name__)


def create_gateway_app() -> FastAPI:
    """Create the unified gateway app with both search and deep-search routes."""
    search_settings = SearchAgentSettings()
    fastapi_app: FastAPI = create_search_app(search_settings)

    # Wire deep search with shared auth
    deep_settings = DeepSearchSettings()

    if search_settings.user_auth_enabled:
        from src.core.middleware.auth import create_unified_auth_dependency

        auth_dep = create_unified_auth_dependency(search_settings)
    else:
        auth_dep = create_api_key_dependency(search_settings)

    wiring = wire_deep_search(deep_settings, auth_dependency=auth_dep)

    # Include deep-search routes
    fastapi_app.include_router(wiring.router)

    # Wrap existing lifespan to include deep-search lifecycle hooks
    original_lifespan = fastapi_app.router.lifespan_context

    @asynccontextmanager
    async def extended_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        for hook in wiring.startup_hooks:
            await hook()
        async with original_lifespan(app) as state:
            yield state
        for hook in wiring.shutdown_hooks:
            await hook()

    fastapi_app.router.lifespan_context = extended_lifespan

    # Mark deep-search as available for diagnostics
    if not hasattr(fastapi_app.state, "features"):
        fastapi_app.state.features = {}
    fastapi_app.state.features["deep_search"] = True

    logger.info("Gateway: deep-search routes mounted")

    return fastapi_app


app = create_gateway_app()
