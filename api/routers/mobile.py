"""Mobile Companion API — lightweight polling endpoints for the Android Companion."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.get("/status")
async def mobile_status():
    """Quick status snapshot for mobile polling."""
    from cores.models import Finding, Target

    from api.scheduler import get_scheduler_stats
    from database.db import SessionLocal

    db = SessionLocal()
    try:
        findings_total = db.query(Finding).count()
        findings_confirmed = db.query(Finding).filter(Finding.status == "confirmed").count()
        targets_active = db.query(Target).filter(Target.status == "active").count()
    finally:
        db.close()

    scheduler = get_scheduler_stats() if callable(get_scheduler_stats) else {}

    return {
        "findings_total": findings_total,
        "findings_confirmed": findings_confirmed,
        "findings_pending": findings_total - findings_confirmed,
        "targets_active": targets_active,
        "scheduler_running": scheduler.get("running", False),
        "next_action": scheduler.get("next_action", ""),
    }


@router.get("/quick-wins")
async def mobile_quick_wins():
    """Top urgent findings needing attention."""
    from cores.models import Finding

    from database.db import SessionLocal

    db = SessionLocal()
    try:
        findings = (
            db.query(Finding)
            .filter(Finding.status.in_(["pending", "validating"]))
            .order_by(Finding.severity.desc())
            .limit(5)
            .all()
        )
        return {
            "quick_wins": [
                {
                    "id": f.id,
                    "title": f.title or f.vulnerability_type or "Unknown",
                    "severity": f.severity or "low",
                    "status": f.status,
                    "target": f.target_name or "",
                }
                for f in findings
            ]
        }
    finally:
        db.close()


@router.post("/subscribe")
async def mobile_subscribe(body: dict[str, Any]):
    """Register a push subscription for the companion."""
    import json as j

    from database.db import SessionLocal
    from database.models import KVStore

    db = SessionLocal()
    try:
        existing = db.query(KVStore).filter(KVStore.key == "mobile:push_subscription").first()
        if existing:
            existing.value = j.dumps(body)
        else:
            db.add(KVStore(key="mobile:push_subscription", value=j.dumps(body)))
        db.commit()
        return {"subscribed": True}
    finally:
        db.close()


@router.post("/notify")
async def mobile_notify(body: dict[str, Any]):
    """Trigger a push notification for the companion."""
    from core.events.event_bus import get_event_bus

    event_bus = get_event_bus()
    event_bus.publish(
        "notification:mobile",
        {
            "title": body.get("title", "CATEYE"),
            "message": body.get("message", ""),
            "url": body.get("url", "/"),
            "type": body.get("type", "info"),
        },
    )
    return {"queued": True}
