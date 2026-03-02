from __future__ import annotations

import logging
from typing import Any

from src.core.jobs.models import JobStatus
from src.core.jobs.service import JobService

logger = logging.getLogger(__name__)


async def run_search(
    ctx: dict[str, Any],
    *,
    query: str,
    session_id: str | None = None,
    tenant_id: str = "default",
) -> dict[str, Any]:
    """ARQ worker function: execute a search pipeline job.

    ``ctx`` is the ARQ worker context dict containing injected
    dependencies (orchestrator, job_service, etc.).
    """
    job_service: JobService = ctx["job_service"]
    job_id: str = ctx["job_id"]

    from src.core.interfaces.orchestrator import Orchestrator
    from src.core.models.context import AgentContext

    orchestrator: Orchestrator = ctx["orchestrator"]

    await job_service.update_status(job_id, status=JobStatus.RUNNING, progress=10)

    try:
        context = AgentContext(
            user_message=query,
            tenant_id=tenant_id,
            session_id=session_id,
        )

        await job_service.update_status(job_id, progress=30)

        result = await orchestrator.run(context)

        await job_service.update_status(job_id, progress=90)

        output = {
            "response": result.response,
            "sources": result.metadata.get("sources", []),
            "query_type": result.metadata.get("query_type", ""),
            "agent_name": result.agent_name,
        }

        await job_service.update_status(
            job_id, status=JobStatus.COMPLETED, progress=100, result=output
        )
        return output

    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        await job_service.update_status(job_id, status=JobStatus.FAILED, error=str(exc))
        raise
