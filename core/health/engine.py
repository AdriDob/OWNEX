"""HealthCenter — unified health monitoring engine.

Consolidates the three legacy health systems into one:
  - SystemHealthEngine (cores/health/engine.py)
  - HealthMonitor (cores/recovery/health_monitor.py)
  - Watchdog (desktop/watchdog.py)

Also bridges to SystemState for persistent snapshots.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any

logger = logging.getLogger("orion.core.health")

CHECK_TIMEOUT = 10  # seconds


@dataclass
class HealthCheck:
    """A single health check (e.g. 'db_reachable', 'event_bus_alive')."""

    name: str
    check_fn: Callable[[], bool]
    category: str = "system"  # system, background, integration, extension
    timeout: float = CHECK_TIMEOUT
    last_run: float = 0.0
    last_ok: bool = True
    last_error: str = ""


@dataclass
class HealthSnapshot:
    """Point-in-time health state."""

    status: str  # green | yellow | red
    checks: dict[str, bool]  # check_name → passed
    timestamp: datetime | None = None
    score: float = 1.0  # 0.0 – 1.0 (ratio of passed / total checks)
    extensions_loaded: int = 0
    extensions_failed: int = 0
    secrets_available: bool = False
    details: dict[str, Any] = field(default_factory=dict)


class HealthCenter:
    """Unified health monitoring engine.

    Status calculation:
      - green:  all checks pass, no errors
      - yellow: some non-critical checks fail
      - red:    critical checks fail
    """

    def __init__(self) -> None:
        self._checks: dict[str, HealthCheck] = {}
        self._lock = Lock()
        self._snapshots: list[HealthSnapshot] = []
        self._max_snapshots = 100
        self._bridge_state: bool = False  # persist to SystemState

    # ── Check registration ───────────────────────────

    def register(self, name: str, check_fn: Callable[[], bool], category: str = "system") -> None:
        with self._lock:
            self._checks[name] = HealthCheck(name=name, check_fn=check_fn, category=category)
            logger.debug("Health check registered: %s (%s)", name, category)

    def unregister(self, name: str) -> None:
        with self._lock:
            self._checks.pop(name, None)

    # ── Running ──────────────────────────────────────

    def run_all(self) -> HealthSnapshot:
        """Run every registered check and return a snapshot."""
        with self._lock:
            results: dict[str, bool] = {}
            errors: dict[str, str] = {}
            for name, check in self._checks.items():
                try:
                    ok = check.check_fn()
                    results[name] = ok
                    check.last_ok = ok
                    check.last_error = ""
                except Exception as exc:
                    results[name] = False
                    check.last_error = str(exc)
                    logger.warning("Health check '%s' failed: %s", name, exc)
                check.last_run = time.time()

            total = len(results)
            passed = sum(1 for v in results.values() if v)
            score = passed / total if total > 0 else 1.0
            status = self._calculate_status(results)
            snapshot = HealthSnapshot(
                status=status,
                score=score,
                timestamp=datetime.now(timezone.utc),
                checks=results,
                details={"errors": errors},
            )
            self._snapshots.append(snapshot)
            if len(self._snapshots) > self._max_snapshots:
                self._snapshots = self._snapshots[-self._max_snapshots :]

        self._persist_snapshot(snapshot)
        logger.info("Health: %s — %d/%d checks passed", status.upper(), passed, total)
        return snapshot

    def run_category(self, category: str) -> HealthSnapshot:
        """Run only checks in a specific category."""
        with self._lock:
            results: dict[str, bool] = {}
            for name, check in self._checks.items():
                if check.category != category:
                    continue
                try:
                    results[name] = check.check_fn()
                    check.last_ok = results[name]
                    check.last_error = ""
                except Exception as exc:
                    results[name] = False
                    check.last_error = str(exc)
                check.last_run = time.time()

            total = len(results)
            passed = sum(1 for v in results.values() if v)
            score = passed / total if total > 0 else 1.0
            status = self._calculate_status(results)
            snapshot = HealthSnapshot(
                status=status,
                score=score,
                timestamp=datetime.now(timezone.utc),
                checks=results,
                details={"category": category},
            )
            self._snapshots.append(snapshot)
            self._persist_snapshot(snapshot)
            return snapshot

    # ── Queries ──────────────────────────────────────

    def status(self) -> str:
        """Latest overall status."""
        if not self._snapshots:
            return "unknown"
        return self._snapshots[-1].status

    def latest(self) -> HealthSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def summary(self) -> dict:
        """Summary dict for API."""
        latest = self.latest()
        total = len(self._checks)
        passed = sum(1 for v in latest.checks.values() if v) if latest else 0
        return {
            "status": latest.status if latest else "unknown",
            "score": latest.score if latest else 0.0,
            "checks_total": total,
            "checks_passed": passed,
            "checks_failed": total - passed,
            "categories": self._category_counts(),
            "last_run": latest.timestamp.isoformat() if latest and latest.timestamp else None,
            "extensions_loaded": latest.extensions_loaded if latest else 0,
            "extensions_failed": latest.extensions_failed if latest else 0,
            "secrets_available": latest.secrets_available if latest else False,
        }

    def list_checks(self) -> list[dict]:
        return [
            {
                "name": c.name,
                "category": c.category,
                "last_ok": c.last_ok,
                "last_error": c.last_error,
                "last_run": c.last_run,
            }
            for c in self._checks.values()
        ]

    # ── Persistence bridge ──────────────────────────

    def enable_persistence(self) -> None:
        """Bridge to SystemState for persistent snapshots."""
        self._bridge_state = True
        logger.info("HealthCenter persistence enabled (bridged to SystemState)")

    def _persist_snapshot(self, snapshot: HealthSnapshot) -> None:
        if not self._bridge_state:
            return
        try:
            from cores.system_state import get_system_state

            state = get_system_state()
            if snapshot.status == "green":
                state.report_healthy("health_center")
            elif snapshot.status == "red":
                state.report_unhealthy(
                    "health_center",
                    error=f"Critical: {sum(1 for v in snapshot.checks.values() if not v)} checks failed",
                )
            elif snapshot.status == "yellow":
                state.report_unhealthy(
                    "health_center",
                    error=f"Degraded: {sum(1 for v in snapshot.checks.values() if not v)} non-critical checks failed",
                )
        except Exception as exc:
            logger.debug("Failed to persist health snapshot: %s", exc)

    # ── Unified summary ─────────────────────────────

    def unified_summary(self) -> dict[str, Any]:
        """Merge HealthCenter checks + process info + DB stats into one dict."""
        import psutil

        from cores.system_state import get_system_state

        # Latest health snapshot
        snap = self.latest()
        status = snap.status if snap else "unknown"
        score = snap.score if snap else 0.0
        checks_passed = sum(1 for v in snap.checks.values() if v) if snap else 0
        checks_total = len(snap.checks) if snap else 0

        # Process info
        pid = os.getpid()
        proc = psutil.Process(pid)
        mem = proc.memory_info()

        # SystemState
        state = get_system_state()
        summary = state.get_summary() if hasattr(state, "get_summary") else {}

        # DB stats
        db_targets = 0
        db_findings = 0
        db_verdicts = 0
        db_confirmed = 0
        try:
            from database.db import SessionLocal
            from database.models import Finding, Target, Verdict

            session = SessionLocal()
            try:
                db_targets = session.query(Target).count()
                db_findings = session.query(Finding).count()
                db_verdicts = session.query(Verdict).count()
                db_confirmed = session.query(Verdict).filter(Verdict.status == "confirmed").count()
            finally:
                session.close()
        except Exception:
            pass

        return {
            "status": status,
            "score": score,
            "checks": {
                "total": checks_total,
                "passed": checks_passed,
                "failed": checks_total - checks_passed,
                "details": {n: v for n, v in (snap.checks.items() if snap else [])},
            },
            "system_state": summary.get("system_state", "unknown"),
            "process": {
                "pid": pid,
                "memory_percent": proc.memory_percent(),
                "memory_rss_mb": round(mem.rss / 1024 / 1024, 1),
                "cpu_percent": proc.cpu_percent(interval=0.3),
                "num_threads": proc.num_threads(),
                "uptime_seconds": state.get_uptime() if hasattr(state, "get_uptime") else 0.0,
            },
            "database": {
                "targets": db_targets,
                "findings": db_findings,
                "verdicts": db_verdicts,
                "confirmed": db_confirmed,
            },
            "registered_checks": self.list_checks(),
        }

    # ── Internal ─────────────────────────────────────

    def _calculate_status(self, results: dict[str, bool]) -> str:
        if not results:
            return "yellow"
        critical_failures = 0
        non_critical_failures = 0
        for name, ok in results.items():
            check = self._checks.get(name)
            if not ok:
                if check and check.category == "system":
                    critical_failures += 1
                else:
                    non_critical_failures += 1
        if critical_failures > 0:
            return "red"
        if non_critical_failures > 0:
            return "yellow"
        return "green"

    def _category_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for check in self._checks.values():
            counts[check.category] = counts.get(check.category, 0) + 1
        return counts


_center: HealthCenter | None = None


def get_health_center() -> HealthCenter:
    global _center
    if _center is None:
        _center = HealthCenter()
    return _center
