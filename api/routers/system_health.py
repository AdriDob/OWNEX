"""System Health API — monitoreo completo del estado de OWNEX.

Expone el estado de todos los subsistemas para que el operador pueda
verificar que todo funciona antes y durante el trabajo diario.

Endpoints:

* ``GET    /api/system/health``      — Resumen de salud global (score 0-100)
* ``GET    /api/system/health/checks`` — Detalle de cada health check
* ``GET    /api/system/health/recovery`` — Estado del motor de recuperación
* ``GET    /api/system/health/circuits`` — Estado de circuit breakers
* ``GET    /api/system/health/sessions`` — Sesiones de trabajo activas
* ``GET    /api/system/health/metrics`` — Métricas del sistema (CPU, RAM, disco)
* ``POST   /api/system/health/recover`` — Forzar intento de recuperación
"""

from __future__ import annotations

import logging
import shutil
from typing import Any

from fastapi import APIRouter, HTTPException

from cores.session_manager import session_manager

logger = logging.getLogger("ownex.api.system_health")

router = APIRouter(tags=["system_health"])


def _get_health_center() -> Any:
    try:
        from cores.health.engine import get_health_center

        return get_health_center()
    except Exception:
        return None


def _get_recovery_engine() -> Any:
    try:
        from cores.recovery.engine import get_recovery_engine

        return get_recovery_engine()
    except Exception:
        return None


def _get_circuit_breakers() -> Any:
    try:
        from cores.recovery.circuit_breaker import CircuitBreakerRegistry

        return CircuitBreakerRegistry()
    except Exception:
        return None


def _get_system_metrics() -> dict[str, Any]:
    """Métricas del sistema sin depender de psutil si no está instalado."""
    try:
        import psutil

        mem = psutil.virtual_memory()
        disk = shutil.disk_usage("/")
        cpu = psutil.cpu_percent(interval=0.5)
        return {
            "cpu_percent": cpu,
            "memory": {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "percent": mem.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": round(disk.used / disk.total * 100, 1),
            },
            "boot_time": psutil.boot_time(),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudieron leer métricas del sistema: %s", exc)
        return {"error": str(exc)}


# ── Endpoints ─────────────────────────────────────────────────────────


@router.get("/api/system/health", summary="Estado de salud global del sistema")
async def system_health() -> dict[str, Any]:
    """Devuelve el score de salud global (0-100) y un resumen de estado."""
    center = _get_health_center()
    if center is None:
        return {
            "status": "unknown",
            "score": 0,
            "message": "Health center no disponible",
        }

    try:
        # Intentar obtener score si el centro lo expone
        score = getattr(center, "get_score", lambda: 0)()
        status = getattr(center, "get_status", lambda: "unknown")()
    except Exception:
        score = 0
        status = "error"

    return {
        "status": status,
        "score": score,
        "app": "OWNEX",
        "version": "7.7.7",
        "message": "Sistema operativo" if score >= 70 else "Sistema degradado",
    }


@router.get(
    "/api/system/health/checks",
    summary="Detalle de cada health check registrado",
)
async def health_checks() -> dict[str, Any]:
    """Lista cada check de salud con su resultado (pass/fail)."""
    center = _get_health_center()
    if center is None:
        return {"checks": [], "message": "Health center no disponible"}

    try:
        checks = center.run_checks() if hasattr(center, "run_checks") else {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error ejecutando health checks: %s", exc)
        checks = {"error": str(exc)}

    return {"checks": checks}


@router.get(
    "/api/system/health/recovery",
    summary="Estado del motor de recuperación",
)
async def health_recovery() -> dict[str, Any]:
    """Estado del RecoveryEngine: fallos detectados, recuperaciones, etc."""
    engine = _get_recovery_engine()
    if engine is None:
        return {"status": "unavailable", "message": "Recovery engine no disponible"}

    try:
        store = getattr(engine, "_store", None)
        recent = store.get_recent_failures(limit=20) if store else []
        return {
            "status": "running" if getattr(engine, "_running", False) else "stopped",
            "recent_failures": recent,
            "recovery_in_progress": list(getattr(engine, "_recovery_in_progress", {}).keys()),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error leyendo recovery engine: %s", exc)
        return {"status": "error", "message": str(exc)}


@router.get(
    "/api/system/health/circuits",
    summary="Estado de circuit breakers",
)
async def health_circuits() -> dict[str, Any]:
    """Estado de cada circuit breaker (abierto/cerrado, fallos consecutivos)."""
    registry = _get_circuit_breakers()
    if registry is None:
        return {"circuits": [], "message": "Circuit breaker registry no disponible"}

    try:
        breakers = registry.get_all() if hasattr(registry, "get_all") else {}
        result = []
        for name, breaker in breakers.items():
            result.append(
                {
                    "name": name,
                    "state": getattr(breaker, "state", "unknown"),
                    "failures": getattr(breaker, "failure_count", 0),
                    "last_failure": getattr(breaker, "last_failure", None),
                }
            )
        return {"circuits": result}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error leyendo circuit breakers: %s", exc)
        return {"circuits": [], "error": str(exc)}


@router.get(
    "/api/system/health/sessions",
    summary="Sesiones de trabajo activas y recientes",
)
async def health_sessions() -> dict[str, Any]:
    """Estado de las sesiones de trabajo (autoguardado)."""
    return session_manager.get_status()


@router.get("/api/system/health/metrics", summary="Métricas del sistema (CPU, RAM, disco)")
async def health_metrics() -> dict[str, Any]:
    """Métricas de recursos del sistema."""
    return _get_system_metrics()


@router.post("/api/system/health/recover", summary="Forzar intento de recuperación")
async def health_recover() -> dict[str, Any]:
    """Intenta recuperar componentes fallidos manualmente."""
    engine = _get_recovery_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Recovery engine no disponible")

    try:
        # Intentar recuperar cada breaker abierto
        registry = _get_circuit_breakers()
        recovered = []
        if registry and hasattr(registry, "get_all"):
            for name, breaker in registry.get_all().items():
                if getattr(breaker, "state", "") == "open":
                    try:
                        breaker.reset()
                        recovered.append(name)
                    except Exception:
                        pass
        return {
            "status": "recovery_attempted",
            "recovered": recovered,
            "message": "Se intentó recuperar " + str(len(recovered)) + " circuitos",
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error en recuperación manual: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
