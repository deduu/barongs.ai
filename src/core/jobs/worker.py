from __future__ import annotations

from typing import Any


def create_worker_settings(
    redis_settings: Any,
    functions: list[Any],
    *,
    max_jobs: int = 10,
    job_timeout: int = 300,
    max_tries: int = 3,
) -> dict[str, Any]:
    """Build an ARQ WorkerSettings-compatible dict.

    Applications call this helper and expose the result as a module-level
    ``WorkerSettings`` class so that ``python -m arq <module>.WorkerSettings``
    picks it up.
    """
    return {
        "redis_settings": redis_settings,
        "functions": functions,
        "max_jobs": max_jobs,
        "job_timeout": job_timeout,
        "max_tries": max_tries,
    }
