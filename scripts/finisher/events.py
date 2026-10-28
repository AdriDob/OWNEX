"""Activity timeline, alerts and remaining-work estimate for FINISHER.

Control Center data layer (megaprompt §14, user spec §4/§6): a persistent,
append-only event log plus rule-based alerts derived from state — never from
model prose. No ML, no prediction theatre: every alert cites the evidence.

Design notes:
  * Events go to `<state_dir>/events.jsonl` (JSON lines, fsync per write).
  * Rotation: cap at 5 MB, keep current + 2 backups. An unbounded log is a
    slow disk-full crash at 3 AM (§17: no infinite logs).
  * State dir is resolved through the state module on every call so tests and
    sandbox runs redirect cleanly (same lesson as worktree paths).
"""

from __future__ import annotations

import contextlib
import json
import os
import time
from datetime import UTC, datetime
from typing import Any

import scripts.finisher.state as state_mod

EVENTS_FILE = "events.jsonl"
MAX_EVENTS_BYTES = 5 * 1024 * 1024
MAX_BACKUPS = 2


def _events_path() -> Any:
    return state_mod.FINISHER_STATE_DIR / EVENTS_FILE


def log_event(
    event_type: str,
    message: str,
    task_id: str | None = None,
    worker_id: str | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one event. Never raises: monitoring must not kill the daemon."""
    event = {
        "ts": datetime.now(UTC).isoformat(),
        "type": event_type,
        "message": message,
        "task_id": task_id,
        "worker_id": worker_id,
        "data": data or {},
    }
    try:
        path = _events_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        _rotate_if_needed(path)
        with open(path, "a") as f:
            f.write(json.dumps(event) + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"Warning: event log write failed: {e}")
    return event


def _rotate_if_needed(path: Any) -> None:
    try:
        if not path.exists() or path.stat().st_size < MAX_EVENTS_BYTES:
            return
        # Shift backups down, drop the oldest. Current file becomes .1.
        oldest = path.with_suffix(f".jsonl.{MAX_BACKUPS}")
        if oldest.exists():
            oldest.unlink()
        for i in range(MAX_BACKUPS - 1, 0, -1):
            src = path.with_suffix(f".jsonl.{i}")
            if src.exists():
                src.rename(path.with_suffix(f".jsonl.{i + 1}"))
        path.rename(path.with_suffix(".jsonl.1"))
    except Exception as e:
        print(f"Warning: event log rotation failed: {e}")


def read_events(
    limit: int = 50,
    task_id: str | None = None,
    event_type: str | None = None,
    include_backups: bool = False,
) -> list[dict[str, Any]]:
    """Newest-first. Filters are exact matches; defaults read current file."""
    try:
        paths = [_events_path()]
        if include_backups:
            for i in range(1, MAX_BACKUPS + 1):
                paths.append(_events_path().with_suffix(f".jsonl.{i}"))
        events: list[dict[str, Any]] = []
        for path in paths:
            if not path.exists():
                continue
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        if task_id is not None:
            events = [e for e in events if e.get("task_id") == task_id]
        if event_type is not None:
            events = [e for e in events if e.get("type") == event_type]
        events.sort(key=lambda e: e.get("ts", ""), reverse=True)
        return events[: max(0, limit)]
    except Exception:
        return []


def evaluate_alerts(state: Any, now: float | None = None) -> list[dict[str, Any]]:
    """Rule-based alerts from persisted state. Each alert carries severity,
    cause and the action needed — never a bare flag."""
    now = now if now is not None else time.time()
    alerts: list[dict[str, Any]] = []

    try:
        from scripts.finisher.state import TaskStatus, WorkerStatus

        # 1. Crash loop: same task failed 2+ times within 10 minutes.
        recent_failures: dict[str, int] = {}
        cutoff = now - 600
        for e in read_events(limit=200, include_backups=False):
            try:
                ts = datetime.fromisoformat(e.get("ts", "")).timestamp()
            except ValueError:
                continue
            if ts < cutoff:
                continue
            if e.get("type") in ("task.failed", "worker.crashed") and e.get("task_id"):
                recent_failures[e["task_id"]] = recent_failures.get(e["task_id"], 0) + 1
        for tid, count in recent_failures.items():
            if count >= 2:
                alerts.append(
                    {
                        "severity": "critical",
                        "rule": "crash_loop",
                        "task_id": tid,
                        "message": f"Task {tid} failed {count}x in 10 min — recovery is guessing; narrow scope or intervene",
                    }
                )

        # 2. Stale gate: pending longer than 30 min with no decision.
        for gid, gate in (state.human_gates or {}).items():
            if gate.get("decision") is not None:
                continue
            try:
                age = now - datetime.fromisoformat(gate.get("created_at", "")).timestamp()
            except ValueError:
                continue
            if age > 1800:
                alerts.append(
                    {
                        "severity": "warning",
                        "rule": "stale_gate",
                        "task_id": gate.get("task_id"),
                        "message": f"Gate {gid} undecided for {age / 60:.0f} min — approve/reject to unblock {gate.get('task_id')}",
                    }
                )

        # 3. No progress: daemon running, tasks unfinished, nothing verified
        #    in the last 30 min (and no active workers to explain it).
        running_workers = [
            w
            for w in (state.workers or {}).values()
            if w.status in (WorkerStatus.RUNNING, WorkerStatus.STARTING, WorkerStatus.ALIVE)
        ]
        unfinished = [
            t
            for t in (state.tasks or {}).values()
            if t.status in (TaskStatus.PENDING, TaskStatus.READY, TaskStatus.RUNNING, TaskStatus.VERIFYING)
        ]
        if unfinished and not running_workers:
            verified_recently = any(
                e.get("type") == "task.verified" and _ts_after(e.get("ts", ""), now - 1800)
                for e in read_events(limit=50, include_backups=False)
            )
            if not verified_recently:
                alerts.append(
                    {
                        "severity": "warning",
                        "rule": "no_progress",
                        "task_id": None,
                        "message": f"{len(unfinished)} task(s) unfinished, no workers active, nothing verified in 30 min",
                    }
                )

        # 4. Runaway worker: active longer than the configured worker timeout.
        try:
            from scripts.finisher.worker import worker_manager

            budget = getattr(worker_manager, "worker_timeout", 1800)
        except Exception:
            budget = 1800
        for wid, w in (state.workers or {}).items():
            if w.status not in (WorkerStatus.RUNNING, WorkerStatus.STARTING):
                continue
            try:
                age = now - datetime.fromisoformat(w.started_at).timestamp()
            except ValueError:
                continue
            if age > budget:
                alerts.append(
                    {
                        "severity": "critical",
                        "rule": "runaway_worker",
                        "task_id": w.task_id,
                        "message": f"Worker {wid} active {age / 60:.0f} min > {budget / 60:.0f} min budget — check or terminate",
                    }
                )
    except Exception as e:
        alerts.append({"severity": "warning", "rule": "alert_engine_error", "task_id": None, "message": str(e)[:200]})

    order = {"critical": 0, "warning": 1}
    alerts.sort(key=lambda a: order.get(a.get("severity", "warning"), 2))
    return alerts


def _ts_after(ts: str, cutoff: float) -> bool:
    try:
        return datetime.fromisoformat(ts).timestamp() >= cutoff
    except ValueError:
        return False


def estimate_remaining(state: Any) -> dict[str, Any]:
    """Remaining verified work + a clearly-labeled rate projection.

    The projection uses the observed verification rate from task evidence
    timestamps when available; otherwise it reports weight/count only and
    says so. No invented velocity.
    """
    try:
        remaining = [t for t in (state.tasks or {}).values() if not t.verified]
        remaining_weight = sum(t.weight for t in remaining)
        by_area: dict[str, float] = {}
        for t in remaining:
            by_area[t.area] = by_area.get(t.area, 0.0) + t.weight

        # Observed rate: verified weight per hour, from evidence timestamps.
        verified_at: list[float] = []
        for t in (state.tasks or {}).values():
            if t.verified and t.verified_at:
                with contextlib.suppress(ValueError):
                    verified_at.append(datetime.fromisoformat(t.verified_at).timestamp())
        projection_hours: float | None = None
        basis = "insufficient history"
        if len(verified_at) >= 2:
            span_h = (max(verified_at) - min(verified_at)) / 3600
            done_w = sum(t.weight for t in (state.tasks or {}).values() if t.verified)
            if span_h > 0 and done_w > 0:
                projection_hours = round(remaining_weight / (done_w / span_h), 1)
                basis = f"{done_w} verified weight over {span_h:.1f}h observed"
        elif len(verified_at) == 1:
            basis = "single data point — projection withheld"

        return {
            "remaining_tasks": len(remaining),
            "remaining_weight": round(remaining_weight, 2),
            "by_area": {k: round(v, 2) for k, v in sorted(by_area.items())},
            "projection_hours": projection_hours,
            "projection_basis": basis,
        }
    except Exception as e:
        return {"error": str(e)[:200]}
