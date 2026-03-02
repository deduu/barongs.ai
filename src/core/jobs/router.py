from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from src.core.jobs.models import JobRecord
from src.core.jobs.service import JobService


def create_job_router(job_service: JobService) -> APIRouter:
    """Create generic job management endpoints."""
    router = APIRouter(prefix="/api/jobs", tags=["jobs"])

    @router.get("/{job_id}", response_model=JobRecord)
    async def get_job(job_id: str) -> JSONResponse:
        record = await job_service.get_status(job_id)
        if record is None:
            return JSONResponse(
                status_code=404,
                content={"error": "not_found", "detail": f"Job {job_id} not found"},
            )
        return JSONResponse(content=record.model_dump(mode="json"))

    @router.get("/{job_id}/stream")
    async def stream_job(job_id: str, request: Request) -> EventSourceResponse:
        async def event_generator():  # type: ignore[no-untyped-def]
            async for event in job_service.stream_events(job_id):
                if await request.is_disconnected():
                    break
                yield {"event": "job_update", "data": str(event)}

        return EventSourceResponse(event_generator())

    @router.delete("/{job_id}")
    async def cancel_job(job_id: str) -> JSONResponse:
        cancelled = await job_service.cancel(job_id)
        if not cancelled:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "cancel_failed",
                    "detail": "Job not found or already finished",
                },
            )
        return JSONResponse(content={"status": "cancelled", "job_id": job_id})

    return router
