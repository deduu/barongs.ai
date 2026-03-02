from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from src.core.jobs.models import JobRecord, JobStatus

logger = logging.getLogger(__name__)


class JobService:
    """Manages background job submission, status polling, and result streaming.

    Wraps ARQ for job enqueueing and uses Redis directly for status
    tracking and pub/sub result streaming.
    """

    _KEY_PREFIX = "bgs:job:"
    _CHANNEL_PREFIX = "bgs:job:events:"

    def __init__(self, redis_client: Any, *, result_ttl_seconds: int = 3600) -> None:
        self._redis = redis_client
        self._result_ttl = result_ttl_seconds
        self._arq_pool: Any | None = None

    async def set_arq_pool(self, pool: Any) -> None:
        """Set the ARQ Redis pool for job enqueueing."""
        self._arq_pool = pool

    async def submit(self, func_name: str, **kwargs: Any) -> str:
        """Enqueue a job and return its ID immediately."""
        job_id = str(uuid.uuid4())
        record = JobRecord(job_id=job_id)

        await self._save_record(record)

        if self._arq_pool is not None:
            await self._arq_pool.enqueue_job(func_name, _job_id=job_id, **kwargs)
        else:
            logger.warning("No ARQ pool configured; job %s will not be processed", job_id)

        return job_id

    async def get_status(self, job_id: str) -> JobRecord | None:
        """Retrieve the current state of a job."""
        raw = await self._redis.get(f"{self._KEY_PREFIX}{job_id}")
        if raw is None:
            return None
        return JobRecord.model_validate_json(raw)

    async def update_status(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        result: Any | None = None,
        error: str | None = None,
    ) -> None:
        """Update a job record (called by workers)."""
        record = await self.get_status(job_id)
        if record is None:
            return

        updates: dict[str, Any] = {}
        if status is not None:
            updates["status"] = status
            if status == JobStatus.RUNNING:
                updates["started_at"] = datetime.now(UTC)
            elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                updates["completed_at"] = datetime.now(UTC)
        if progress is not None:
            updates["progress"] = progress
        if result is not None:
            updates["result"] = result
        if error is not None:
            updates["error"] = error

        record = record.model_copy(update=updates)
        await self._save_record(record)

        # Publish event for SSE subscribers
        event = {"status": record.status.value, "progress": record.progress}
        if record.result is not None:
            event["result"] = record.result
        if record.error is not None:
            event["error"] = record.error
        await self._redis.publish(
            f"{self._CHANNEL_PREFIX}{job_id}",
            json.dumps(event, default=str),
        )

    async def cancel(self, job_id: str) -> bool:
        """Cancel a pending job. Returns True if cancellation succeeded."""
        record = await self.get_status(job_id)
        if record is None:
            return False
        if record.status not in (JobStatus.PENDING, JobStatus.RUNNING):
            return False
        await self.update_status(job_id, status=JobStatus.CANCELLED)
        return True

    async def stream_events(self, job_id: str) -> AsyncIterator[dict[str, Any]]:
        """Yield job events via Redis pub/sub until completion."""
        # First emit current state
        record = await self.get_status(job_id)
        if record is None:
            return
        yield {"status": record.status.value, "progress": record.progress}

        if record.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return

        pubsub = self._redis.pubsub()
        await pubsub.subscribe(f"{self._CHANNEL_PREFIX}{job_id}")
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                event = json.loads(message["data"])
                yield event
                if event.get("status") in (
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value,
                ):
                    break
        finally:
            await pubsub.unsubscribe(f"{self._CHANNEL_PREFIX}{job_id}")
            await pubsub.aclose()

    async def _save_record(self, record: JobRecord) -> None:
        await self._redis.set(
            f"{self._KEY_PREFIX}{record.job_id}",
            record.model_dump_json(),
            ex=self._result_ttl,
        )
