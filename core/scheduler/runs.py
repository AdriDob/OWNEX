"""Scheduler Run Ledger — trazabilidad e idempotencia de jobs (spec §12).

Cada ejecución registra: job_id, run_id, started_at, finished_at, status,
attempt, error. Persistencia JSONL append-only bajo OWNEX_DATA_DIR/runtime/
(patrón data-dir del proyecto). El lock por job evita doble ejecución
simultánea del MISMO job dentro del proceso y, donde fcntl está disponible,
entre procesos (dos api.main no deben correr el mismo job a la vez).
"""

from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunRecord:
    """Campos exactos del spec BACKEND ALPHA 1.0 §12."""

    job_id: str
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    status: str = "running"  # running | success | failed | skipped_locked
    attempt: int = 1
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "attempt": self.attempt,
            "error": self.error,
        }


def _default_ledger_path() -> Path:
    """OWNEX_DATA_DIR aware (patrón workbank): frozen → %LOCALAPPDATA%/OWNEX."""
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[2] / "data"
    runtime = root / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    return runtime / "scheduler_runs.jsonl"


@contextmanager
def job_lock(job_id: str, lock_dir: Path):
    """Lock exclusivo por job (fcntl cuando existe; degrada sin lock).

    Yields True si se obtuvo el lock, False si otro proceso lo sostiene —
    el caller saltea la ejecución (idempotencia cross-proceso).
    """
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{job_id}.lock"
    try:
        import fcntl  # POSIX
    except ImportError:
        yield True  # plataforma sin flock: guard in-proceso basta
        return
    handle = open(lock_path, "w")  # noqa: SIM115 — cierre garantizado en finally
    try:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
            handle.close()
    except BaseException:
        handle.close()
        raise


class SchedulerRunLedger:
    """Registro persistente + contadores de intento por job."""

    def __init__(self, ledger_path: str | Path | None = None) -> None:
        self._path = Path(ledger_path or _default_ledger_path())

    def append(self, record: RunRecord) -> None:
        """Best-effort: la observabilidad nunca rompe el scheduler."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "a") as fh:
                fh.write(json.dumps(record.to_dict()) + "\n")
        except Exception:
            pass

    def next_attempt(self, job_id: str, *, tail: int = 200) -> int:
        """Intento N para este job según las últimas entradas (restart-safe)."""
        try:
            if not self._path.exists():
                return 1
            lines = self._path.read_text().strip().splitlines()[-tail:]
            count = sum(1 for line in lines if line.strip() and json.loads(line).get("job_id") == job_id)
            return count + 1 if count else 1
        except Exception:
            return 1

    def recent(self, limit: int = 50) -> list[dict]:
        """Últimas corridas (visible vía API si un consumidor la pide)."""
        try:
            if not self._path.exists():
                return []
            lines = [ln for ln in self._path.read_text().splitlines() if ln.strip()]
            return [json.loads(ln) for ln in lines[-limit:]]
        except Exception:
            return []
