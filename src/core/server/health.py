from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe. Returns 200 if the service is running."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    """Readiness probe. Runs registered dependency checks.

    Returns 200 if all checks pass, 503 if any fail.
    Applications register checks via ``app.state.readiness_checks``,
    a list of ``(name, async_callable_returning_bool)`` tuples.
    """
    if getattr(request.app.state, "shutting_down", False):
        return JSONResponse(
            status_code=503,
            content={"status": "shutting_down"},
        )

    checks: list[tuple[str, Any]] = getattr(request.app.state, "readiness_checks", [])

    if not checks:
        return JSONResponse(content={"status": "ready"})

    results: dict[str, str] = {}
    all_ok = True

    for name, probe in checks:
        try:
            ok = await probe()
        except Exception:
            logger.warning("Readiness check '%s' raised an exception", name, exc_info=True)
            ok = False
        results[name] = "ok" if ok else "failing"
        if not ok:
            all_ok = False

    status_code = 200 if all_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ok else "degraded",
            "checks": results,
        },
    )
