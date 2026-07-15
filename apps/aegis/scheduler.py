"""AEGIS scheduler jobs — recurring maintenance and automation."""

from __future__ import annotations

import logging

from apps.aegis.models import AegisTarget, ScanResult
from core.database.manager import get_db_manager

logger = logging.getLogger("orion.aegis.scheduler")


def check_active_targets() -> dict[str, int]:
    """Check for active targets and log their status."""
    db = get_db_manager().get_session("aegis")
    try:
        active = db.query(AegisTarget).filter(AegisTarget.status == "active").count()
        pending = db.query(AegisTarget).filter(AegisTarget.status == "pending").count()
        logger.info("[AEGIS] Targets: %d active, %d pending", active, pending)
        return {"active": active, "pending": pending}
    finally:
        db.close()


def cleanup_stale_scans() -> dict[str, int]:
    """Remove scan results older than 90 days."""
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    db = get_db_manager().get_session("aegis")
    try:
        stale = db.query(ScanResult).filter(ScanResult.created_at < cutoff).count()
        if stale:
            db.query(ScanResult).filter(ScanResult.created_at < cutoff).delete()
            db.commit()
            logger.info("[AEGIS] Cleaned %d stale scan results", stale)
        return {"cleaned": stale}
    finally:
        db.close()
