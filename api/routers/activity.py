"""Activity feed API — recent system events for Mission Control.

Aggregates recent events from the CoreEventBus (in-memory + persisted)
into a flat, frontend-friendly timeline.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter

from core.events.event_bus import get_core_event_bus

logger = logging.getLogger("orion.activity")
router = APIRouter(prefix="/api/activity", tags=["activity"])

_SEVERITY_BY_EVENT: dict[str, str] = {
    "finding:critical": "high",
    "finding:confirmed": "high",
    "finding:new": "medium",
    "finding:rejected": "medium",
    "report:accepted": "high",
    "report:rejected": "high",
    "report:generated": "medium",
    "payout:received": "high",
    "opportunity:found": "medium",
    "opportunity:claimed": "medium",
    "system:error": "high",
    "system:warning": "medium",
}


def _classify(event: str) -> tuple[str, str]:
    """Map event name to (type, severity) for the frontend."""
    if event.startswith("scheduler:"):
        return "scheduler", "low"
    if event.startswith("loop:"):
        return "cycle", "low"
    if event.startswith("payout:") or event.startswith("revenue:"):
        return "payout", "high"
    if event.startswith("report:"):
        return "report", "medium"
    if event.startswith("finding:"):
        return "finding", "medium"
    if event.startswith("opportunity:"):
        return "opportunity", "medium"
    if event.startswith("system:") or event.startswith("health:"):
        return "system", "medium"
    return "activity", "low"


@router.get("")
async def activity_feed(hours: int = 24, limit: int = 50):
    """Recent activity from the event bus, newest first.

    Params: ``hours`` — only events newer than this window (default 24).
    ``limit`` — max events to return (default 50, max 200).
    """
    try:
        bus = get_core_event_bus()
        history = bus.get_history(limit=200)
    except Exception as exc:
        logger.warning("[ACTIVITY] Event bus unavailable: %s", exc)
        history = []

    cutoff = datetime.now(UTC).timestamp() - hours * 3600
    events: list[dict] = []
    for rec in reversed(history):
        ts = float(rec.get("timestamp", 0))
        if ts < cutoff:
            continue
        event = str(rec.get("event", ""))
        data = rec.get("data") or {}
        etype, severity = _classify(event)
        if event in _SEVERITY_BY_EVENT:
            severity = _SEVERITY_BY_EVENT[event]
        message = str(data.get("title") or data.get("message") or data.get("detail") or event)
        events.append(
            {
                "id": f"{event}:{ts}",
                "event": event,
                "type": etype,
                "severity": severity,
                "title": message,
                "message": message,
                "timestamp": datetime.fromtimestamp(ts, UTC).isoformat(),
            }
        )
        if len(events) >= min(max(limit, 1), 200):
            break

    return {"events": events}
