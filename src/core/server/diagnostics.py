from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from src.core.utils.sanitize import SENSITIVE_KEYS, sanitize_dict

# Extra keys specific to settings that contain secrets
_SETTINGS_SENSITIVE = frozenset(
    set(SENSITIVE_KEYS) | {"jwt_secret_key", "database_url", "redis_url"}
)


def create_diagnostics_router() -> APIRouter:
    """Create a diagnostics router that introspects the running app.

    Returns mounted routes, sanitized settings, and feature flags.
    Applications can set ``app.state.features`` (dict) to expose
    which optional modules are loaded.
    """
    router = APIRouter(prefix="/api", tags=["diagnostics"])

    @router.get("/diagnostics")
    async def diagnostics(request: Request) -> dict[str, Any]:
        app = request.app

        # Collect all routes with their methods
        routes: list[dict[str, Any]] = []
        for route in app.routes:
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if path is not None and methods is not None:
                routes.append({"path": path, "methods": sorted(methods)})

        # Sanitized settings (if available)
        settings_data: dict[str, Any] | None = None
        settings = getattr(app.state, "settings", None)
        if settings is not None:
            raw = settings.model_dump() if hasattr(settings, "model_dump") else vars(settings)
            settings_data = sanitize_dict(
                {k: v for k, v in raw.items() if _is_serializable(v)},
                extra_keys=_SETTINGS_SENSITIVE,
            )

        # Feature flags
        features: dict[str, Any] = getattr(app.state, "features", {})

        return {
            "routes": routes,
            "settings": settings_data,
            "features": features,
        }

    return router


def _is_serializable(value: Any) -> bool:
    """Check if a value can be JSON-serialized (skip callables, complex objects)."""
    return isinstance(value, (str, int, float, bool, list, dict, type(None)))
