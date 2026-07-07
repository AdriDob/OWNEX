import json
from typing import Any

from fastapi import APIRouter, Query, Request

from cores.gateway.schemas import error, ok
from cores.notifications.push import get_push_router
from cores.opportunity import get_engine
from database import db

router = APIRouter(prefix="/api/mobile", tags=["mobile"])


@router.get("/dashboard")
async def mobile_dashboard():
    """Lightweight dashboard summary for mobile clients."""
    opp_engine = get_engine()
    opp_metrics = opp_engine.get_metrics()

    return ok({
        "opportunities_total": opp_metrics.get("opportunities_total", 0),
        "opportunities_high_priority": opp_metrics.get("by_priority", {}).get("high", 0),
        "targets_total": _count("targets"),
        "findings_total": _count("findings"),
        "quick_wins_total": _count("quick_wins"),
        "pipeline_active": _count("pipeline", "status = 'running'"),
    })


@router.get("/opportunities")
async def mobile_opportunities(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Lightweight opportunity list for mobile."""
    opp_engine = get_engine()
    opportunities = opp_engine.get_all()

    items = [
        {
            "id": o.id,
            "name": o.name,
            "category": o.category,
            "priority": o.priority or "medium",
            "score": o.score.overall if o.score else 0,
            "estimated_payout": o.estimated_payout,
        }
        for o in opportunities
    ]

    return ok({"opportunities": items, "total": len(items)})


@router.get("/quick-wins")
async def mobile_quick_wins(limit: int = Query(10, ge=1, le=50)):
    """Lightweight quick-wins list for mobile."""
    rows = db.query("SELECT id, title, category, estimated_payout, confidence FROM quick_wins ORDER BY confidence DESC LIMIT ?", (limit,))
    items = [
        {
            "id": r["id"],
            "title": r["title"],
            "category": r["category"] or "general",
            "estimated_payout": r["estimated_payout"] or 0,
            "confidence": r["confidence"] or 0,
        }
        for r in rows
    ]
    return ok({"quick_wins": items, "total": len(items)})


@router.get("/assistant-summary")
async def mobile_assistant_summary():
    """Last 5 assistant messages, minimal payload."""
    rows = db.query(
        "SELECT role, content, timestamp FROM assistant_messages ORDER BY id DESC LIMIT 5",
    )
    items = [
        {"role": r["role"], "content": r["content"][:200], "timestamp": r.get("timestamp")}
        for r in rows
    ]
    return ok({"messages": items})


@router.get("/notifications")
async def mobile_notifications(limit: int = Query(20, ge=1, le=100)):
    """Recent notifications for mobile."""
    rows = db.query(
        "SELECT id, type, message, is_read, created_at FROM notifications ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    items = [
        {
            "id": r["id"],
            "type": r["type"],
            "message": r["message"],
            "is_read": bool(r["is_read"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]
    return ok({"notifications": items, "total": len(items)})


@router.get("/search")
async def mobile_search(q: str = Query("", min_length=1)):
    """Unified search across targets, opportunities, and findings."""
    results: dict[str, list[dict[str, Any]]] = {"targets": [], "opportunities": [], "findings": []}

    # Search targets
    rows = db.query(
        "SELECT id, name, domain FROM targets WHERE name LIKE ? OR domain LIKE ? LIMIT 10",
        (f"%{q}%", f"%{q}%"),
    )
    results["targets"] = [{"id": r["id"], "name": r["name"], "domain": r.get("domain")} for r in rows]

    # Search opportunities
    opp_engine = get_engine()
    all_opps = opp_engine.get_all()
    matched = [o for o in all_opps if q.lower() in o.name.lower()]
    results["opportunities"] = [
        {"id": o.id, "name": o.name, "category": o.category}
        for o in matched[:10]
    ]

    # Search findings
    rows = db.query(
        "SELECT id, target_id, title, severity FROM findings WHERE title LIKE ? LIMIT 10",
        (f"%{q}%",),
    )
    results["findings"] = [{"id": r["id"], "target_id": r["target_id"], "title": r["title"], "severity": r["severity"]} for r in rows]

    return ok(results)


@router.post("/push/subscribe")
async def mobile_push_subscribe(request: Request):
    """Register a device for push notifications."""
    body = await request.json()
    device_id = body.get("device_id")
    subscription = body.get("subscription", {})
    if not device_id:
        return error("device_id required", version="1.0")
    router = get_push_router()
    router.subscribe(device_id, "mobile")
    # Persist subscription info per device
    db.execute(
        "INSERT OR REPLACE INTO push_subscriptions (device_id, subscription_json) VALUES (?, ?)",
        (device_id, json.dumps(subscription)),
    )
    return ok({"status": "subscribed", "device_id": device_id})


@router.post("/push/unsubscribe")
async def mobile_push_unsubscribe(request: Request):
    body = await request.json()
    device_id = body.get("device_id")
    if not device_id:
        return error("device_id required", version="1.0")
    router = get_push_router()
    router.unsubscribe(device_id, "mobile")
    db.execute("DELETE FROM push_subscriptions WHERE device_id = ?", (device_id,))
    return ok({"status": "unsubscribed", "device_id": device_id})


@router.get("/summary")
async def mobile_summary():
    """Ultra-light dashboard snapshot — not even full dashboard, just the signal."""
    opp_engine = get_engine()
    opp_metrics = opp_engine.get_metrics()
    high_priority = opp_metrics.get("by_priority", {}).get("high", 0)
    return ok({
        "high_priority_opportunities": high_priority,
        "unread_notifications": _count("notifications", "is_read = 'false'"),
        "quick_wins_available": _count("quick_wins"),
        "system_status": _get_system_status(),
    })


def _get_system_status() -> str:
    try:
        from cores.system_state import get_system_state
        state = get_system_state()
        return state.get_summary().get("system_state", "UNKNOWN")
    except Exception:
        return "UNKNOWN"


_ALLOWED_TABLES = frozenset({"targets", "findings", "quick_wins", "pipeline", "notifications", "push_subscriptions", "assistant_messages"})


def _count(table: str, where: str = "1=1") -> int:
    if table not in _ALLOWED_TABLES:
        return 0
    from sqlalchemy import text
    with db.SessionLocal() as session:
        row = session.execute(text(f"SELECT COUNT(*) as cnt FROM {table} WHERE {where}")).fetchone()
        return row[0] if row else 0
