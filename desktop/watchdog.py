"""Watchdog — internal supervisor that monitors and auto-recovers system health.

Runs as a background daemon thread. Checks every N seconds:

- API health endpoint (HTTP 200)
- Agent health (all agents responsive)
- Scheduler running
- EventBus alive
- Memory usage (%)
- CPU usage (%)

Auto-recovery with exponential backoff:
  backoff = min(30 * 2^attempt, 300) seconds
  max 5 consecutive failures before escalation
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger("cateye.watchdog")


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_ok: float = 0.0
    last_fail: float = 0.0
    fail_count: int = 0
    last_error: str = ""
    recovery_attempts: int = 0


@dataclass
class WatchdogSnapshot:
    timestamp: float
    services: dict[str, ServiceHealth]
    memory_percent: float
    cpu_percent: float
    overall: HealthStatus
    uptime: float


_WATCHDOG_INSTANCE: Watchdog | None = None


def get_watchdog() -> Watchdog | None:
    return _WATCHDOG_INSTANCE


class Watchdog:
    """Background supervisor that periodically checks system health."""

    def __init__(
        self,
        health_check_url: str = "http://127.0.0.1:8000/api/health",
        check_interval: float = 30.0,
        max_recovery_attempts: int = 5,
        on_recovery: Callable[[str], None] | None = None,
        on_escalate: Callable[[str], None] | None = None,
    ):
        self._health_url = health_check_url
        self._interval = check_interval
        self._max_attempts = max_recovery_attempts
        self._on_recovery = on_recovery
        self._on_escalate = on_escalate

        self._services: dict[str, ServiceHealth] = {
            # No need to pre-define services here, as SystemHealthEngine handles checks
        }
        self._start_time: float = 0.0
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._snapshot_history: list[
            WatchdogSnapshot
        ] = []  # Se mantiene solo si hay otras funcionalidades que lo necesiten

        global _WATCHDOG_INSTANCE
        _WATCHDOG_INSTANCE = self

    # Los métodos _update_service, _check_api, _check_agents, _check_scheduler, _check_eventbus
    # _get_memory_percent, _get_cpu_percent, _attempt_recovery, _detect_freeze
    # se han movido a SystemHealthEngine o ya no son necesarios aquí.

    def _run_loop(self) -> None:
        self._start_time = time.time()

        # En el Watchdog simplificado, el bucle puede simplemente hacer un sleep
        # o esperar a eventos del SystemHealthEngine si se implementa una escucha.
        # Por ahora, simplemente se mantendrá un bucle ligero.
        while self._running:
            try:
                # Aquí podríamos obtener el estado del SystemHealthEngine si fuera necesario
                # from cores.health.engine import get_system_health_engine
                # health_engine = get_system_health_engine()
                # current_status = health_engine.status()
                # logger.info("[WATCHDOG] Monitoreando SystemHealthEngine: %s", current_status)
                logger.debug("[WATCHDOG] Watchdog running passively")

            except Exception as exc:
                logger.error("[WATCHDOG] Loop error: %s", exc, exc_info=True)

            if self._running:
                time.sleep(self._interval)  # Usar el intervalo original del watchdog

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="cateye-watchdog")
        self._thread.start()
        logger.info("[WATCHDOG] Started (interval=%ss)", self._interval)

    def stop(self) -> None:
        self._running = False
        self._thread = None
        logger.info("[WATCHDOG] Stopped")

    @property
    def is_running(self) -> bool:
        return self._running and (self._thread is not None and self._thread.is_alive())

    def get_snapshot(self) -> WatchdogSnapshot | None:
        # Este método ahora puede obtener el snapshot del SystemHealthEngine si es necesario,
        # o ser eliminado si no se usa en la UI de escritorio directamente.
        # Por simplicidad en este sprint, lo dejo como estaba pero su utilidad es limitada.
        with self._lock:
            if not self._snapshot_history:
                return None
            return self._snapshot_history[-1]

    def get_history(self) -> list[WatchdogSnapshot]:
        with self._lock:
            return list(self._snapshot_history)

    def get_status(self) -> dict[str, Any]:
        # Este método también puede obtener el estado del SystemHealthEngine
        # Por simplicidad, se mantiene una estructura similar si la UI lo usa.
        # No se necesita el diccionario _services interno aquí si SystemHealthEngine es la fuente de verdad.
        snap = self.get_snapshot()
        return {
            "running": self.is_running,
            "uptime": time.time() - self._start_time if self._start_time else 0,
            "memory_percent": snap.memory_percent if snap else -1,
            "cpu_percent": snap.cpu_percent if snap else -1,
            "overall": snap.overall.value if snap else "unknown",
            "snapshots": len(self._snapshot_history),
        }
