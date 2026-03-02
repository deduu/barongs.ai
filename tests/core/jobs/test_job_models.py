"""Tests for job Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.jobs.models import JobRecord, JobStatus


class TestJobStatus:
    def test_values(self):
        assert JobStatus.PENDING == "pending"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"


class TestJobRecord:
    def test_defaults(self):
        record = JobRecord(job_id="j-123")
        assert record.job_id == "j-123"
        assert record.status == JobStatus.PENDING
        assert record.created_at is not None
        assert record.started_at is None
        assert record.completed_at is None
        assert record.result is None
        assert record.error is None
        assert record.progress == 0

    def test_completed_record(self):
        record = JobRecord(
            job_id="j-456",
            status=JobStatus.COMPLETED,
            result={"answer": "42"},
            progress=100,
        )
        assert record.status == JobStatus.COMPLETED
        assert record.result == {"answer": "42"}
        assert record.progress == 100

    def test_failed_record(self):
        record = JobRecord(
            job_id="j-789",
            status=JobStatus.FAILED,
            error="LLM timeout",
        )
        assert record.status == JobStatus.FAILED
        assert record.error == "LLM timeout"

    def test_progress_bounds(self):
        with pytest.raises(ValidationError):
            JobRecord(job_id="j-1", progress=-1)
        with pytest.raises(ValidationError):
            JobRecord(job_id="j-2", progress=101)
