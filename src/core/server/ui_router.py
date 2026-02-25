from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


def create_ui_router(frontend_dir: Path) -> APIRouter:
    """Return an APIRouter that serves the SPA.

    - ``GET /`` → ``index.html``
    - ``GET /{path}`` → file if it exists, else ``index.html`` (SPA catch-all)
    """
    router = APIRouter(tags=["ui"])
    index = frontend_dir / "index.html"

    @router.get("/", include_in_schema=False)
    async def serve_ui() -> FileResponse:
        return FileResponse(index)

    @router.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str) -> FileResponse:
        file = frontend_dir / path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(index)

    return router
