"""Tests for JobService — submit, poll, cancel, stream."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest

from src.core.jobs.models import JobStatus
from src.core.jobs.service import JobService


@pytest.fixture
async def redis_client():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.fixture
def job_service(redis_client):
    return JobService(redis_client, result_ttl_seconds=300)


class TestJobSubmit:
    async def test_returns_job_id(self, job_service):
        job_id = await job_service.submit("run_search", query="test")
        assert isinstance(job_id, str)
        assert len(job_id) > 0

    async def test_creates_pending_record(self, job_service):
        job_id = await job_service.submit("run_search", query="test")
        record = await job_service.get_status(job_id)
        assert record is not None
        assert record.status == JobStatus.PENDING
        assert record.progress == 0

    async def test_enqueues_to_arq_pool(self, job_service):
        pool = MagicMock()
        pool.enqueue_job = AsyncMock()
        await job_service.set_arq_pool(pool)

        job_id = await job_service.submit("run_search", query="hello")
        pool.enqueue_job.assert_awaited_once_with("run_search", _job_id=job_id, query="hello")


class TestJobStatus:
    async def test_get_nonexistent_job(self, job_service):
        assert await job_service.get_status("nonexistent") is None

    async def test_update_to_running(self, job_service):
        job_id = await job_service.submit("run_search", query="test")
        await job_service.update_status(job_id, status=JobStatus.RUNNING, progress=10)

        record = await job_service.get_status(job_id)
        assert record is not None
        assert record.status == JobStatus.RUNNING
        assert record.started_at is not None
        assert record.progress == 10

    async def test_update_to_completed(self, job_service):
        job_id = await job_service.submit("run_search", query="test")
        await job_service.update_status(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result={"answer": "42"},
        )

        record = await job_service.get_status(job_id)
        assert record is not None
        assert record.status == JobStatus.COMPLETED
        assert record.completed_at is not None
        assert record.result == {"answer": "42"}
        assert record.progress == 100

    async def test_update_to_failed(self, job_service):
        job_id = await job_service.submit("run_search", query="test")
        await job_service.update_status(job_id, status=JobStatus.FAILED, error="LLM timeout")

        record = await job_service.get_status(job_id)
        assert record is not None
        assert record.status == JobStatus.FAILED
        assert record.error == "LLM timeout"


class TestJobCancel:
    async def test_cancel_pending_job(self, job_service):
        job_id = await job_service.submit("run_search", query="test")
        assert await job_service.cancel(job_id) is True

        record = await job_service.get_status(job_id)
        assert record is not None
        assert record.status == JobStatus.CANCELLED

    async def test_cancel_nonexistent_job(self, job_service):
        assert await job_service.cancel("nonexistent") is False

    async def test_cancel_completed_job_fails(self, job_service):
        job_id = await job_service.submit("run_search", query="test")
        await job_service.update_status(job_id, status=JobStatus.COMPLETED, progress=100)
        assert await job_service.cancel(job_id) is False
