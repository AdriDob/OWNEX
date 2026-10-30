"""Observation API — System health, scheduler, agents, recovery, backups.

Single endpoint for system observability.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter


def _db_path() -> Path:
    r"""Ruta real de la base, tal como la resuelve el motor de la app.

    Antes cada endpoint hacía `os.path.expanduser("~/.ownex/database/cateye.db")`:

    - rompía en Windows instalado (la app usa %LOCALAPPDATA%\OWNEX);
    - ignoraba OWNEX_DATA_DIR, que el resto del sistema sí respeta;
    - apuntaba a `cateye.db`, una base huérfana sin escribirse desde el
      2026-08-25 — el router reportaba sobre datos que ya no existían.

    Ahora se deriva de `database.db.DATABASE_URL`: donde el motor realmente abre
    la base. Una sola fuente de verdad, sin una segunda resolución que pueda
    divergir.
    """
    from database.db import DATABASE_URL

    if not DATABASE_URL.startswith("sqlite"):
        raise RuntimeError(f"observation requiere SQLite, no {DATABASE_URL.split(':', 1)[0]}")
    return Path(DATABASE_URL.removeprefix("sqlite:///"))


def _data_dir() -> Path:
    return _db_path().parent.parent


def _backup_dir() -> Path:
    return _data_dir() / "backups"


router = APIRouter(prefix="/api/observation", tags=["observation"])


@router.get("/health")
async def get_health():
    """Get complete system health status."""
    import psutil
    from sqlalchemy import text

    from database.db import SessionLocal

    pid = os.getpid()
    proc = psutil.Process(pid)
    mem = proc.memory_info()

    # DB health
    db_ok = False
    db_size = 0.0
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_ok = True
            db_path = _db_path()
            if db_path.exists():
                db_size = db_path.stat().st_size / 1024 / 1024
    except Exception:
        pass

    # Scheduler
    scheduler_status = "unknown"
    try:
        from api.scheduler import get_scheduler_status

        scheduler_status = get_scheduler_status().get("status", "unknown")
    except Exception:
        pass

    # Notifications
    notification_channels = []
    try:
        from cores.notifications.hub import get_hub

        hub = get_hub()
        notification_channels = list(hub._channels.keys())
    except Exception:
        pass

    return {
        "status": "operational" if db_ok else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "system": {
            "pid": pid,
            "memory_mb": round(mem.rss / 1024 / 1024, 1),
            "memory_percent": round(proc.memory_percent(), 1),
            "cpu_percent": proc.cpu_percent(interval=0.1),
            "threads": proc.num_threads(),
            "uptime_seconds": round(
                (datetime.now(UTC) - datetime.fromtimestamp(proc.create_time(), UTC)).total_seconds(), 0
            ),
        },
        "database": {
            "status": "connected" if db_ok else "disconnected",
            "size_mb": round(db_size, 2),
        },
        "scheduler": {
            "status": scheduler_status,
        },
        "notifications": {
            "channels": notification_channels,
            "count": len(notification_channels),
        },
    }


@router.get("/recovery")
async def get_recovery_status():
    """Get recovery engine status (real engine, best-effort, never raises)."""
    try:
        from cores.recovery import get_recovery_engine

        engine = get_recovery_engine()
        status = engine.status()
        try:
            status["version_recovery"] = engine.get_version_recovery_status()
        except Exception:
            status["version_recovery"] = {"available": False}
        status["features"] = [
            "stale_scan_recovery",
            "crash_recovery",
            "retry_with_backoff",
            "dead_letter_queue",
            "version_rollback",
        ]
        return status
    except Exception as exc:  # noqa: BLE001 — status never 500s
        return {"status": "unavailable", "error": str(exc)}


@router.get("/backup")
async def get_backup_status():
    """Get backup status."""
    db_path = _db_path()
    backup_path = _backup_dir()

    has_backup = os.path.exists(backup_path)
    backup_count = 0
    if has_backup:
        import contextlib

        with contextlib.suppress(Exception):
            backup_count = len([f for f in os.listdir(backup_path) if f.endswith(".db")])

    return {
        "database_path": str(db_path),
        "backup_path": str(backup_path),
        "has_backups": has_backup,
        "backup_count": backup_count,
        "auto_backup": True,
        "recommendation": "Run `python run.py --backup` to create a backup" if not has_backup else "Backups configured",
    }


@router.post("/backup")
async def create_backup():
    """Create a database backup."""
    import shutil

    db_path = _db_path()
    backup_dir = _backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"cateye_{timestamp}.db"

    try:
        shutil.copy2(db_path, backup_path)
        return {
            "status": "ok",
            "backup_path": str(backup_path),
            "size_mb": round(backup_path.stat().st_size / 1024 / 1024, 2),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
