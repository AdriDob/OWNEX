"""Mobile Companion API — lightweight polling endpoints for the Android Companion."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.post("/copilot/chat")
async def mobile_copilot_chat(request: dict[str, Any]):
    """Chat with COPILOT from mobile - uses mobile-friendly providers."""
    from cores.copilot.providers.router import TASK_CHAT, get_provider_router

    messages = request.get("messages", [])
    router = get_provider_router()

    # Mobile-friendly routing: Freebuff -> NVIDIA -> LocalFallback
    response = await router.route(task_type=TASK_CHAT, messages=messages)

    return {
        "content": response.content,
        "provider": response.provider,
        "model": response.model,
        "error": response.error,
        "duration_ms": response.duration_ms,
    }


@router.post("/copilot/decision")
async def mobile_copilot_decision(request: dict[str, Any]):
    """Ask COPILOT for a decision from mobile."""
    from cores.copilot.providers.router import TASK_REASON, get_provider_router

    messages = request.get("messages", [])
    router = get_provider_router()

    # Mobile-friendly routing: Freebuff -> FCC -> NVIDIA -> LocalFallback
    response = await router.route(task_type=TASK_REASON, messages=messages)

    return {
        "content": response.content,
        "provider": response.provider,
        "model": response.model,
        "error": response.error,
        "duration_ms": response.duration_ms,
    }


@router.post("/copilot/approve")
async def mobile_copilot_approve(request: dict[str, Any]):
    """Approve a COPILOT decision from mobile."""

    decision_id = request.get("decision_id")
    approved = request.get("approved", False)
    reason = request.get("reason", "")

    # Simple approval - in production this would use the full COPILOT workflow
    return {
        "decision_id": decision_id,
        "approved": approved,
        "reason": reason,
        "status": "approved" if approved else "rejected",
    }


@router.get("/providers/status")
async def mobile_providers_status():
    """Health check of all AI providers for mobile."""
    from cores.ai.provider import PROVIDER_CATALOG
    from cores.copilot.providers.router import get_provider_router

    router = get_provider_router()
    provider_status = {}

    # Check COPILOT providers
    for provider in router.providers:
        try:
            is_available = await provider.check()
            provider_status[provider.name] = {
                "available": is_available,
                "type": "copilot",
            }
        except Exception:
            provider_status[provider.name] = {
                "available": False,
                "type": "copilot",
                "error": "check failed",
            }

    # Check catalog providers (Ollama, etc.)
    for spec in PROVIDER_CATALOG:
        provider_status[spec.id] = {
            "available": False,  # Would need to implement check for each
            "type": "catalog",
            "label": spec.label,
        }

    return {
        "providers": provider_status,
        "total": len(provider_status),
        "available": sum(1 for p in provider_status.values() if p.get("available", False)),
    }


@router.get("/status")
async def mobile_status():
    """Quick status snapshot for mobile polling."""
    from api.scheduler import get_scheduler_stats
    from database.db import SessionLocal
    from database.models import Finding, Target

    db = SessionLocal()
    try:
        findings_total = db.query(Finding).count()
        findings_confirmed = db.query(Finding).filter(Finding.status == "confirmed").count()
        targets_active = db.query(Target).filter(Target.active == True).count()  # noqa: E712
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
    from database.db import SessionLocal
    from database.models import Finding

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
    from cores.events.event_bus import get_event_bus

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
