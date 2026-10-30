"""SystemHealthEngine — evaluates global system health and emits status events."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any

import httpx  # AÑADIR
import psutil  # Asegurarse de que psutil está importado.
from sqlalchemy import text

from cores.health.scoring import (
    HealthScoringSystem,
    HealthStatus,
    classify_health,
)
from cores.recovery.engine import get_recovery_engine
from cores.recovery.healing_rules import FailureType

logger = logging.getLogger("cateye.health.engine")

DEFAULT_INTERVAL = 10.0


class SystemHealthEngine:
    """Central health evaluation engine.

    Collects metrics from all subsystems, computes a 0-100 health score,
    and emits health status events to the EventBus.
    """

    def __init__(self) -> None:
        self._scoring = HealthScoringSystem()
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._interval = DEFAULT_INTERVAL
        self._last_status: HealthStatus | None = None
        self._eventbus: Any = None
        self._agent_bus: Any = None
        self._consecutive_fails: int = 0  # AÑADIR
        self._mem_leak_warnings: int = 0  # AÑADIR
        self._prev_mem: float = -1.0  # AÑADIR
        self._snapshot_history: list[dict[str, Any]] = []  # Para detección de freeze, AÑADIR

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="CATEYE-health-engine",
        )
        self._thread.start()
        logger.info("[HEALTH] Engine started (interval=%ss)", self._interval)

    def stop(self) -> None:
        self._running = False
        self._thread = None
        logger.info("[HEALTH] Engine stopped")

    def set_interval(self, interval: float) -> None:
        self._interval = max(2.0, interval)

    # ── Metrics collection ────────────────────────────────────────────

    def _collect_metrics(self) -> dict[str, Any]:
        metrics: dict[str, Any] = {
            "eventbus_failures": 0,
            "agent_crashes": 0,
            "scheduler_latency_sec": 0,
            "db_lock_count": 0,
            "pipeline_retries": 0,
            "recovery_attempts": 0,
            "memory_percent": 0.0,
            "cpu_percent": 0.0,  # AÑADIR
            "open_circuits": 0,
            "uptime_hours": 0,
            "total_pipelines": 0,
            "api_status": "unknown",  # AÑADIR
            "agents_status": "unknown",  # AÑADIR
            "scheduler_status": "unknown",  # AÑADIR
        }

        try:
            # Metrics de memoria y CPU (desde Watchdog)
            process = psutil.Process()
            metrics["memory_percent"] = process.memory_percent()
            metrics["cpu_percent"] = process.cpu_percent(interval=0.1)  # Utilizar un intervalo pequeño
            metrics["uptime_hours"] = (time.time() - process.create_time()) / 3600
        except Exception as exc:
            logger.debug("Failed to collect memory/uptime/cpu metrics: %s", exc)

        # Comprobaciones de API (desde Watchdog)
        api_health_url = "http://127.0.0.1:8000/api/health"
        try:
            r = httpx.get(api_health_url, timeout=5.0)
            metrics["api_status"] = "ok" if r.status_code == 200 else "failed"
        except Exception as exc:
            metrics["api_status"] = f"failed ({exc})"
            logger.debug("Failed to check API health: %s", exc)

        try:
            base = api_health_url.rsplit("/api/health", 1)[0]
            agents_health_url = f"{base}/api/agents/health"
            r = httpx.get(agents_health_url, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                all_healthy = all(
                    agent.get("status") == "running"
                    for agent in (data if isinstance(data, list) else data.get("agents", data.get("data", [])))
                )
                metrics["agents_status"] = "ok" if all_healthy else "failed"
            else:
                metrics["agents_status"] = "failed"
        except Exception as exc:
            metrics["agents_status"] = f"failed ({exc})"
            logger.debug("Failed to check agents health: %s", exc)

        try:
            base = api_health_url.rsplit("/api/health", 1)[0]
            scheduler_status_url = f"{base}/api/scheduler/status"
            r = httpx.get(scheduler_status_url, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                running = data.get("running", data.get("status") == "running")
                metrics["scheduler_status"] = "ok" if running else "failed"
            else:
                metrics["scheduler_status"] = "failed"
        except Exception as exc:
            metrics["scheduler_status"] = f"failed ({exc})"
            logger.debug("Failed to check scheduler status: %s", exc)

        # Métrica de DB connectivity (desde HealthMonitor - aunque ya hay algo similar con honey metrics)
        try:
            from database import db

            db.init_db()
            session = db.SessionLocal()
            # Intentar una query simple para verificar conectividad
            session.execute(text("SELECT 1")).scalar_one()
            session.close()
            metrics["db_connectivity"] = "ok"
        except Exception as exc:
            metrics["db_connectivity"] = "failed"
            logger.debug("Failed to check DB connectivity: %s", exc)

        try:
            from cores.recovery import get_recovery_engine

            engine = get_recovery_engine()
            status = engine.status()
            cb_snaps = engine.circuit_breaker_snapshots()
            metrics["open_circuits"] = sum(1 for s in cb_snaps.values() if s["state"] == "open")
            metrics["recovery_attempts"] = len(status.get("recovery_in_progress", {}))
        except Exception as exc:
            logger.debug("Failed to collect recovery engine metrics: %s", exc)

        try:
            from cores.recovery import get_recovery_store

            store = get_recovery_store()
            history = store.get_recovery_history(limit=50)
            metrics["eventbus_failures"] = sum(1 for h in history if "eventbus" in h.get("component", ""))
            metrics["agent_crashes"] = sum(1 for h in history if "agent" in h.get("component", ""))
            metrics["db_lock_count"] = sum(1 for h in history if "db" in h.get("component", ""))
        except Exception as exc:
            logger.debug("Failed to collect recovery store metrics: %s", exc)

        try:
            from cores.agents import get_all_agents

            agents = get_all_agents()
            metrics["agent_crashes"] += sum(1 for a in agents if a.tasks_failed > 0)
        except Exception as exc:
            logger.debug("Failed to collect agent metrics: %s", exc)

        try:
            from cores.agents.bus import get_agent_bus

            bus = get_agent_bus()
            agent_history = bus.get_history(limit=30)
            metrics["pipeline_retries"] = sum(
                1 for e in agent_history if hasattr(e, "event_type") and "failed" in str(e.event_type)
            )
        except Exception as exc:
            logger.debug("Failed to collect agent bus metrics: %s", exc)

        # Honey metrics — what the system is actually producing
        try:
            from database import db, models

            db.init_db()
            session = db.SessionLocal()
            honey = {}
            try:
                honey["findings_total"] = session.query(models.Finding).count()
                honey["findings_confirmed"] = (
                    session.query(models.Finding).filter(models.Finding.status == "confirmed").count()
                )
                honey["findings_pending"] = (
                    session.query(models.Finding).filter(models.Finding.status == "open").count()
                )
                honey["reports_total"] = session.query(models.Report).count() if hasattr(models, "Report") else 0
                honey["targets_active"] = session.query(models.Target).count()
                honey["verdicts_total"] = session.query(models.Verdict).count()
            except Exception as exc:
                logger.debug("Failed to collect honey metrics: %s", exc)
            finally:
                session.close()
            if not any(v is None for v in honey.values()):
                metrics.update(honey)
        except Exception as exc:
            logger.debug("Failed to collect DB honey metrics: %s", exc)

        return metrics

    # ── Recovery & Freeze Detection (desde Watchdog) ────────────────────

    def _attempt_recovery(self, component_name: str, error_message: str = "") -> bool:
        """Attempt to recover a failed component via RecoveryEngine."""
        try:
            engine = get_recovery_engine()
            failure_type_map = {
                "api_status": "api_unresponsive",
                "agents_status": "agent_crashed",
                "scheduler_status": "scheduler_dead",
                "db_connectivity": "db_stuck",
                "eventbus_failures": "eventbus_stuck",
                "memory_percent": "high_memory",
                "cpu_percent": "high_cpu",
            }
            ft = FailureType(failure_type_map.get(component_name, "unknown"))
            initiated = engine.report_failure(
                component=component_name,
                error_message=error_message or f"Health check failed for {component_name}",
                failure_type=ft,
                details={"source": "system_health_engine"},
            )
            if initiated:
                logger.info("[HEALTH] Recovery initiated for %s via RecoveryEngine", component_name)
                return True
            logger.warning("[HEALTH] Recovery engine declined recovery for %s", component_name)
        except Exception as exc:
            logger.error("[HEALTH] Recovery engine error for %s: %s", component_name, exc)
        return False

    def _detect_freeze(self, history: list[dict[str, Any]]) -> bool:
        """Detect if the system is frozen (identical status across last N snapshots)."""
        if len(history) < 3:
            return False
        recent = history[-3:]
        # Suponemos que cada snapshot tiene una clave "overall_status" o similar
        if all(s.get("overall_status") == recent[0].get("overall_status") for s in recent):
            # Check if timestamp deltas are consistent (process not truly frozen)
            timestamps = [s.get("timestamp", 0.0) for s in recent]
            deltas = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
            # Si los deltas de tiempo son consistentes con el intervalo, no está congelado, solo está en el mismo estado.
            if all(d < self._interval * 3 for d in deltas):
                return False  # Normal operation, just stuck in same status
            logger.warning("[HEALTH] Possible freeze detected — identical status across %d checks", len(recent))
            return True
        return False

    def _persist_snapshot(self, score: float, status: HealthStatus, metrics: dict) -> None:
        """Save health snapshot to persistent store — the hive remembers."""
        try:
            from cores.recovery.persistence import get_recovery_store

            store = get_recovery_store()
            snapshot = {
                "score": round(score, 1),
                "status": status.value,
                "trend": self._scoring.trend(),
                "metrics": {k: v for k, v in metrics.items() if isinstance(v, (int, float, str))},
                "timestamp": datetime.now(UTC).timestamp(),  # Añadir timestamp
                "overall_status": status.value,  # Para la detección de freeze
            }
            self._snapshot_history.append(snapshot)  # Almacenar en la historia local
            if len(self._snapshot_history) > 1000:  # Limitar el tamaño de la historia
                self._snapshot_history = self._snapshot_history[-500:]

            store.save_health_snapshot(source="system_health_engine", data=snapshot)
        except Exception as exc:
            logger.debug("[HEALTH] Snapshot persistence skipped: %s", exc)

    # ── Health evaluation loop ────────────────────────────────────────

    def _run_loop(self) -> None:
        while self._running:
            try:
                metrics = self._collect_metrics()
                score = self._scoring.record(metrics)
                status = classify_health(score)

                with self._lock:
                    changed = self._last_status != status
                    self._last_status = status

                event_type = {
                    HealthStatus.OK: "system:ready",
                    HealthStatus.DEGRADED: "system:degraded",
                    HealthStatus.CRITICAL: "system:error",
                    HealthStatus.RECOVERING: "system:ready",
                }.get(status, "system:ready")

                self._emit_health_event(event_type, status.value, score)
                self._persist_snapshot(score, status, metrics)

                if changed:
                    logger.info(
                        "[HEALTH] Status changed to %s (score=%.1f, trend=%s)",
                        status.value,
                        score,
                        self._scoring.trend(),
                    )

                logger.debug(
                    "[HEALTH] Score=%.1f status=%s metrics=%s",
                    score,
                    status.value,
                    metrics,
                )

                # ── Recovery and Freeze Detection (desde Watchdog) ──────────
                all_ok = (
                    all(v == "ok" for k, v in metrics.items() if "status" in k or "connectivity" in k)
                    and metrics["memory_percent"] < 80.0
                    and metrics["cpu_percent"] < 90.0
                )

                if not all_ok:
                    self._consecutive_fails += 1
                    # Intentar recuperación de componentes fallidos
                    for metric_key, metric_value in metrics.items():
                        if "status" in metric_key and metric_value != "ok":
                            self._attempt_recovery(metric_key, error_message=metric_value)
                        if "connectivity" in metric_key and metric_value != "ok":
                            self._attempt_recovery(metric_key, error_message=metric_value)

                    # Detección de memory leak (adaptado del Watchdog)
                    mem_pct = metrics["memory_percent"]
                    if self._prev_mem > 0 and mem_pct > 0 and (mem_pct - self._prev_mem) > 10.0:
                        self._mem_leak_warnings += 1
                        if self._mem_leak_warnings >= 3:
                            logger.critical("[HEALTH] MEMORY LEAK CONFIRMED — initiating recovery")
                            self._attempt_recovery("memory_percent", error_message="Memory leak confirmed")
                            self._mem_leak_warnings = 0  # Reset para evitar repetición constante
                    else:
                        self._mem_leak_warnings = max(0, self._mem_leak_warnings - 1)
                    self._prev_mem = mem_pct

                    # Freeze detection
                    if self._consecutive_fails >= 3 and self._detect_freeze(self._snapshot_history):
                        logger.critical("[HEALTH] SYSTEM FROZEN — initiating emergency recovery")
                        # Intentar recuperación para todos los componentes críticos
                        for metric_key in [
                            "api_status",
                            "agents_status",
                            "scheduler_status",
                            "db_connectivity",
                            "eventbus_failures",
                        ]:
                            self._attempt_recovery(metric_key, error_message="System frozen")

                else:
                    self._consecutive_fails = 0
                    self._mem_leak_warnings = 0
                    self._prev_mem = -1.0  # Reset al estar saludable

            except Exception as exc:
                logger.error("[HEALTH] Engine loop error: %s", exc, exc_info=True)

            if self._running:
                time.sleep(self._interval)

    def _emit_health_event(self, event_type: str, severity: str, score: float) -> None:
        try:
            from cores.events.event_bus import get_event_bus

            bus = get_event_bus()
            bus.publish(
                event_type,
                source="system_health_engine",
                severity=severity,
                health_score=round(score, 1),
                trend=self._scoring.trend(),
                timestamp=datetime.now(UTC).isoformat(),
            )
        except Exception as exc:
            logger.debug("[HEALTH] Event emission skipped: %s", exc)

    # ── Status ────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "interval": self._interval,
                "current_score": self._scoring.current_score(),
                "current_status": self._scoring.current_status().value,
                "trend": self._scoring.trend(),
                "snapshots": len(self._scoring.history()),
            }

    def get_health_summary(self) -> dict[str, Any]:
        """Get comprehensive health summary for external consumers."""
        with self._lock:
            checks = {}
            for check in self._checks.values():
                checks[check.name] = {
                    "status": check.status.value,
                    "message": check.message,
                    "last_run": check.last_run.isoformat() if check.last_run else None,
                    "latency_ms": check.latency_ms,
                }
            return {
                "overall": {
                    "score": self._scoring.current_score(),
                    "status": self._scoring.current_status().value,
                    "trend": self._scoring.trend(),
                },
                "checks": checks,
                "running": self._running,
            }

    def get_scoring_system(self) -> HealthScoringSystem:
        return self._scoring


_ENGINE: SystemHealthEngine | None = None
_ENGINE_LOCK = threading.Lock()


def get_system_health_engine() -> SystemHealthEngine:
    global _ENGINE
    if _ENGINE is None:
        with _ENGINE_LOCK:
            if _ENGINE is None:
                _ENGINE = SystemHealthEngine()
    return _ENGINE


def reset_system_health_engine() -> None:
    global _ENGINE
    if _ENGINE is not None:
        _ENGINE.stop()
    _ENGINE = None


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
    """Unified registry-based health monitoring engine.

    Status calculation:
      - green:  all checks pass, no errors
      - yellow: some non-critical checks fail (or nothing registered yet)
      - red:    critical (system-category) checks fail
    """

    def __init__(self) -> None:
        self._checks: dict[str, HealthCheck] = {}
        self._lock = Lock()
        self._snapshots: list[HealthSnapshot] = []
        self._max_snapshots = 100
        self._bridge_state: bool = False  # persist to SystemState

    # ── Check registration ────────────────────────────

    def register(self, name: str, check_fn: Callable[[], bool], category: str = "system") -> None:
        with self._lock:
            self._checks[name] = HealthCheck(name=name, check_fn=check_fn, category=category)
            logger.debug("Health check registered: %s (%s)", name, category)

    def unregister(self, name: str) -> None:
        with self._lock:
            self._checks.pop(name, None)

    # ── Running ───────────────────────────────────────

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
                timestamp=datetime.now(UTC),
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
                timestamp=datetime.now(UTC),
                checks=results,
                details={"category": category},
            )
            self._snapshots.append(snapshot)
            self._persist_snapshot(snapshot)
            return snapshot

    # ── Queries ───────────────────────────────────────

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

    # ── Persistence bridge ────────────────────────────

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

    # ── Unified summary ───────────────────────────────

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

    # ── Internal ──────────────────────────────────────

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


# Alias for backward compatibility
_health_center: HealthCenter | None = None


def get_health_center() -> HealthCenter:
    """Canonical registry-based health center (register/run_all/summary).

    This is the API consumed by health endpoints, lifespan boot, the AI
    control plane and stability router — consolidated here from the legacy
    twin so there is exactly one implementation.
    """
    global _health_center
    if _health_center is None:
        _health_center = HealthCenter()
    return _health_center


def reset_health_center() -> None:
    global _health_center
    _health_center = None
