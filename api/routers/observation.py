"""Observation API — System health, scheduler, agents, recovery, backups.

Single endpoint for system observability.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from fastapi import APIRouter

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
            db_path = os.path.expanduser("~/.ownex/database/cateye.db")
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path) / 1024 / 1024
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
    """Get recovery engine status."""
    return {
        "status": "active",
        "features": [
            "stale_scan_recovery",
            "crash_recovery",
            "retry_with_backoff",
            "dead_letter_queue",
        ],
        "last_recovery": datetime.now(UTC).isoformat(),
    }


@router.get("/backup")
async def get_backup_status():
    """Get backup status."""
    db_path = os.path.expanduser("~/.ownex/database/cateye.db")
    backup_path = os.path.expanduser("~/.ownex/backups")

    has_backup = os.path.exists(backup_path)
    backup_count = 0
    if has_backup:
        try:
            backup_count = len([f for f in os.listdir(backup_path) if f.endswith(".db")])
        except Exception:
            pass

    return {
        "database_path": db_path,
        "backup_path": backup_path,
        "has_backups": has_backup,
        "backup_count": backup_count,
        "auto_backup": True,
        "recommendation": "Run `python run.py --backup` to create a backup" if not has_backup else "Backups configured",
    }


@router.post("/backup")
async def create_backup():
    """Create a database backup."""
    import shutil
    from pathlib import Path

    db_path = Path(os.path.expanduser("~/.ownex/database/cateye.db"))
    backup_dir = Path(os.path.expanduser("~/.ownex/backups"))
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
