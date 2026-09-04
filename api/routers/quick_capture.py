"""Quick Capture API Router — zero-friction finding intake (hotkeys/tray)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

from cores.intake.quick_capture import get_quick_capture_engine

logger = logging.getLogger("ownex.api.quick_capture")

router = APIRouter(prefix="/api/quick-capture", tags=["quick-capture"])


@router.post("/")
async def api_capture(
    url: str,
    title: str | None = None,
    category: str = "bug_bounty",
    severity: str = "medium",
    notes: str = "",
    source: str = "hotkey",
) -> dict[str, Any]:
    """Capture a URL/finding quickly and return the enriched record."""
    engine = get_quick_capture_engine()
    rec = engine.capture(
        url=url,
        title=title or url,
        category=category,
        severity=severity,
        notes=notes,
        source=source,
    )
    return rec.to_dict()


@router.post("/{capture_id}/queue")
async def api_queue(capture_id: str) -> dict[str, Any]:
    """Push a capture into the Work Bank."""
    return get_quick_capture_engine().queue_to_workbank(capture_id)


@router.get("/{capture_id}")
async def api_get(capture_id: str) -> dict[str, Any]:
    """Get a single capture."""
    rec = get_quick_capture_engine().get(capture_id)
    if not rec:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Capture not found")
    return rec.to_dict()


@router.get("/")
async def api_list(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    """List recent captures."""
    recs = get_quick_capture_engine().list(limit)
    return {"count": len(recs), "captures": [r.to_dict() for r in recs]}
