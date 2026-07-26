"""HealthMonitor — periodic health check loop that feeds the RecoveryEngine.

Checks every N seconds by delegating to HealthCenter:
- EventBus alive and publishing
- Agent bus alive
- All agents responsive
- Scheduler running
- Database connectivity
- Memory usage (leak detection)

Checks live in core/health/checks.py — this is a thin polling loop.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from cores.recovery.engine import RecoveryEngine, get_recovery_engine

logger = logging.getLogger("cateye.recovery.health_monitor")

DEFAULT_INTERVAL = 8.0
MAX_HISTORY = 200

_CHECK_TO_COMPONENT: dict[str, str] = {
    "event_bus": "eventbus",
    "agent_bus": "agent_bus",
    "agents_health": "agents",
    "scheduler": "scheduler",
    "database": "database",
    "memory": "memory",
}


class HealthMonitor:
    """Background thread loop that checks all system components periodically.

    Delegates actual checks to HealthCenter. Reports state changes to RecoveryEngine.
    """

    def __init__(
        self,
        engine: RecoveryEngine | None = None,
        interval: float = DEFAULT_INTERVAL,
        health_url: str = "http://127.0.0.1:8000/api/health",
    ) -> None:
        self._engine = engine or get_recovery_engine()
        self._interval = interval
        self._health_url = health_url
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._history: list[dict[str, Any]] = []
        self._last_health: dict[str, bool] = {
            "eventbus": True,
            "agent_bus": True,
            "agents": True,
            "scheduler": True,
            "database": True,
            "memory": True,
        }

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="CATEYE-health-monitor",
        )
        self._thread.start()
        logger.info("[HEALTH] Monitor started (interval=%ss)", self._interval)

    def stop(self) -> None:
        self._running = False
        self._thread = None
        logger.info("[HEALTH] Monitor stopped")

    def _run_loop(self) -> None:
        while self._running:
            try:
                self._check_all()
            except Exception as exc:
                logger.error("[HEALTH] Monitor loop error: %s", exc, exc_info=True)

            if self._running:
                time.sleep(self._interval)

    def _check_all(self) -> None:
        """Delegate all checks to HealthCenter, then feed results to RecoveryEngine."""
        try:
            from core.health.engine import get_health_center

            center = get_health_center()
            snapshot = center.run_all()
            center_checks = snapshot.checks
        except Exception:
            center_checks = {}

        results: dict[str, bool] = {}
        for hc_name, comp_name in _CHECK_TO_COMPONENT.items():
            ok = center_checks.get(hc_name, False)
            results[comp_name] = ok

        for legacy in ("eventbus", "agent_bus", "agents", "database", "memory"):
            if legacy not in results:
                results[legacy] = center_checks.get(legacy, False)

        all_ok = True
        degraded = False

        for name, ok in results.items():
            with self._lock:
                changed = self._last_health.get(name) != ok
                self._last_health[name] = ok

            if not ok:
                all_ok = False
                if name in ("eventbus", "agent_bus", "database"):
                    degraded = True
                if changed:
                    self._engine.report_failure(
                        component=name,
                        error_message=f"Health check failed for {name}",
                    )
            else:
                if changed:
                    self._engine.report_success(component=name)

        if all_ok:
            logger.info("[HEALTH] All components healthy")
        elif degraded:
            logger.warning("[HEALTH] Critical component failure")
        else:
            logger.warning("[HEALTH] Non-critical component failure")

        snapshot = {
            "timestamp": time.time(),
            "checks": dict(self._last_health),
            "all_ok": all_ok,
        }
        with self._lock:
            self._history.append(snapshot)
            if len(self._history) > MAX_HISTORY:
                self._history[:] = self._history[-MAX_HISTORY // 2 :]

    def _check_eventbus(self) -> bool:
        try:
            from core.health.engine import get_health_center

            center = get_health_center()
            snap = center.run_category("system")
            return snap.checks.get("event_bus", False)
        except Exception as exc:
            logger.warning("[HEALTH] EventBus check failed: %s", exc)
            return False

    def _check_agent_bus(self) -> bool:
        try:
            from core.health.engine import get_health_center

            center = get_health_center()
            snap = center.run_category("system")
            return snap.checks.get("agent_bus", False)
        except Exception:
            return False

    def _check_agents(self) -> bool:
        try:
            from core.health.engine import get_health_center

            center = get_health_center()
            snap = center.run_all()
            return snap.checks.get("agents_health", False)
        except Exception:
            return False

    def _check_database(self) -> bool:
        try:
            from core.health.engine import get_health_center

            center = get_health_center()
            snap = center.run_category("system")
            return snap.checks.get("database", False)
        except Exception as exc:
            logger.warning("[HEALTH] Database check failed: %s", exc)
            return False

    def _check_memory(self) -> bool:
        try:
            from core.health.engine import get_health_center

            center = get_health_center()
            snap = center.run_all()
            return snap.checks.get("memory", False)
        except Exception:
            return True

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "interval": self._interval,
                "last_checks": dict(self._last_health),
                "history_count": len(self._history),
            }


_MONITOR: HealthMonitor | None = None
_MONITOR_LOCK = threading.Lock()


def get_health_monitor() -> HealthMonitor:
    global _MONITOR
    if _MONITOR is None:
        with _MONITOR_LOCK:
            if _MONITOR is None:
                _MONITOR = HealthMonitor()
    return _MONITOR


def reset_health_monitor() -> None:
    global _MONITOR
    if _MONITOR is not None:
        _MONITOR.stop()
    _MONITOR = None
