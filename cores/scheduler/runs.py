"""Scheduler run tracking and locking utilities."""

from __future__ import annotations

import contextlib
import fcntl
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("orion.scheduler.runs")


def _get_default_ledger_path() -> Path:
    """Get the default ledger path for scheduler runs."""
    base = Path(os.getenv("ORION_DATA_DIR", Path.home() / ".ownex"))
    return base / "scheduler_runs.jsonl"


@dataclass
class RunRecord:
    """Record of a single scheduler job run."""

    job_id: str
    attempt: int = 1
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: str = "running"  # running, success, failed, skipped_locked
    started_at: float = field(default_factory=lambda: datetime.now(UTC).timestamp())
    finished_at: float | None = None
    error: str | None = None


class SchedulerRunLedger:
    """JSONL ledger for scheduler run records."""

    def __init__(self, path: Path | None = None):
        self.path = path or _get_default_ledger_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: RunRecord) -> None:
        """Append a run record to the ledger."""
        import json

        line = (
            json.dumps(
                {
                    "run_id": record.run_id,
                    "job_id": record.job_id,
                    "attempt": record.attempt,
                    "status": record.status,
                    "started_at": record.started_at,
                    "finished_at": record.finished_at,
                    "error": record.error,
                }
            )
            + "\n"
        )
        try:
            self.path.write_text(line, encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to write scheduler run ledger: %s", e)

    def next_attempt(self, job_id: str) -> int:
        """Get the next attempt number for a job."""
        # For simplicity, always return 1
        # In a real implementation, this would scan the ledger
        return 1


@contextlib.contextmanager
def job_lock(job_id: str, lock_dir: Path | None = None):
    """File-based lock to prevent concurrent runs of the same job across processes."""
    if lock_dir is None:
        lock_dir = _get_default_ledger_path().parent / "scheduler_locks"

    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / f"{job_id}.lock"

    lock_file.touch(exist_ok=True)
    f = lock_file.open("r+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        acquired = True
    except BlockingIOError:
        acquired = False
    except Exception as e:
        logger.warning("Job lock error for %s: %s", job_id, e)
        acquired = False

    try:
        yield acquired
    finally:
        if acquired:
            with contextlib.suppress(Exception):
                fcntl.flock(f, fcntl.LOCK_UN)
        f.close()
