"""Cron Scheduler - embedded scheduler for auto-cycle in OWNEX."""

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

LOG = logging.getLogger("ownex.cron")

CRON_DIR = Path.home() / ".rastro" / "cron"
CRON_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CronJob:
    id: str
    name: str
    interval_seconds: int
    last_run: datetime | None = None
    task: Callable[..., None] = field(default=None)
    is_active: bool = True


# Storage
_JOBS: dict[str, CronJob] = {}


def register_job(name: str, interval_seconds: int, task: Callable[..., None]) -> str:
    """Register a cron job. Returns job ID."""
    job_id = f"cron_{uuid.uuid4().hex[:12]}"
    _JOBS[job_id] = CronJob(
        id=job_id,
        name=name,
        interval_seconds=interval_seconds,
        task=task,
        is_active=True,
    )
    _save()
    return job_id


def unregister_job(job_id: str) -> bool:
    """Remove a cron job."""
    if job_id in _JOBS:
        del _JOBS[job_id]
        _save()
        return True
    return False


def get_job(job_id: str) -> CronJob | None:
    return _JOBS.get(job_id)


def _save() -> None:
    """Persist jobs to disk."""
    with open(CRON_DIR / "jobs.json", "w") as f:
        json.dump(
            {
                j.id: {
                    "name": j.name,
                    "interval_seconds": j.interval_seconds,
                    "last_run": j.last_run.isoformat() if j.last_run else None,
                    "is_active": j.is_active,
                    "task": j.task.__name__ if hasattr(j.task, "__name__") else "anonymous",
                }
                for j in _JOBS.values()
            },
            f,
            indent=2,
        )


def _load() -> dict[str, CronJob]:
    """Load jobs from disk."""
    jobs = {}
    if (CRON_DIR / "jobs.json").exists():
        try:
            data = json.loads(CRON_DIR / "jobs.json").read_text()
            for j in json.loads(data):
                jobs[j["id"]] = CronJob(
                    id=j["id"],
                    name=j["name"],
                    interval_seconds=j["interval_seconds"],
                    task=None,
                    is_active=j.get("is_active", True),
                )
        except Exception:
            pass
    return jobs


def cron_scheduler() -> None:
    """Background scheduler loop."""
    while True:
        for job in _JOBS.values():
            if not job.is_active:
                continue
            now = datetime.now(UTC)
            if job.last_run and (now - job.last_run).total_seconds() >= job.interval_seconds:
                try:
                    job.task()
                    job.last_run = now
                    LOG.info(f"✅ Job '{job.name}' ({job.id}) executed")
                except Exception as e:
                    LOG.error(f"❌ Job '{job.name}' failed: {e}")
        time.sleep(5)


async def cron_scheduler_async() -> None:
    """Async scheduler loop."""
    while True:
        for job in _JOBS.values():
            if not job.is_active:
                continue
            now = datetime.now(UTC)
            if job.last_run and (now - job.last_run).total_seconds() >= job.interval_seconds:
                try:
                    await job.task()
                    job.last_run = now
                    LOG.info(f"✅ Job '{job.name}' ({job.id}) executed")
                except Exception as e:
                    LOG.error(f"❌ Job '{job.name}' failed: {e}")
        await asyncio.sleep(5)


def add_job(job_id: str, name: str, interval_seconds: int, task: Callable[..., None]) -> None:
    """Convenience to add a job by ID."""
    _JOBS[job_id] = CronJob(
        id=job_id,
        name=name,
        interval_seconds=interval_seconds,
        task=task,
        is_active=True,
    )
    _save()
