"""Availability API — endpoints for human availability intelligence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.direct_work_engine.availability import (
    can_accommodate_task,
    get_availability_engine,
    get_availability_snapshot,
    get_available_hours,
    recommend_max_task_hours,
)

router = APIRouter(prefix="/api/availability", tags=["availability"])


# ── Pydantic Models ──


class CalendarImportRequest(BaseModel):
    ics_path: str


class BusyBlockRequest(BaseModel):
    start: str  # ISO datetime
    end: str  # ISO datetime
    title: str = ""


class AvailableBlockRequest(BaseModel):
    start: str  # ISO datetime
    end: str  # ISO datetime
    title: str = "focus"


class AccommodateCheck(BaseModel):
    required_hours: float
    horizon: str = "today"  # today | this_week | this_month


# ── Endpoints ──


@router.get("/snapshot")
async def get_availability_snapshot_endpoint() -> dict[str, Any]:
    """Get current availability snapshot (today/week/month)."""
    return get_availability_snapshot().to_dict()


@router.get("/hours")
async def get_available_hours_endpoint(horizon: str = "today") -> dict[str, Any]:
    """Get available hours for a given horizon."""
    try:
        hours = get_available_hours(horizon)
        return {"horizon": horizon, "hours": hours}
    except KeyError:
        raise HTTPException(
            status_code=400, detail=f"Invalid horizon: {horizon}. Use: today, this_week, this_month"
        ) from None


@router.post("/can-accommodate")
async def check_can_accommodate(request: AccommodateCheck) -> dict[str, Any]:
    """Check if a task requiring N hours fits in available time."""
    try:
        can_fit, remaining = can_accommodate_task(request.required_hours, request.horizon)
        return {
            "can_accommodate": can_fit,
            "available_hours": get_available_hours(request.horizon),
            "required_hours": request.required_hours,
            "remaining_hours": round(remaining, 2),
        }
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid horizon: {request.horizon}") from None


@router.get("/max-task-hours")
async def get_max_task_hours(horizon: str = "today") -> dict[str, Any]:
    """Get recommended max task duration (80% rule)."""
    try:
        max_hours = recommend_max_task_hours(horizon)
        return {"horizon": horizon, "max_recommended_hours": round(max_hours, 1)}
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid horizon: {horizon}") from None


@router.get("/blocks")
async def get_time_blocks(days: int = 7) -> dict[str, Any]:
    """Get available/busy time blocks for the next N days."""
    engine = get_availability_engine()
    blocks = engine.get_time_blocks(days)
    return {
        "days": days,
        "blocks": [{"start": b.start, "end": b.end, "type": b.type, "title": b.title} for b in blocks],
    }


@router.post("/calendar/import")
async def import_calendar(request: CalendarImportRequest) -> dict[str, Any]:
    """Import events from an ICS file."""
    engine = get_availability_engine()
    try:
        count = engine.import_calendar_ics(request.ics_path)
        return {"status": "success", "events_imported": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/calendar/busy")
async def add_busy_block(request: BusyBlockRequest) -> dict[str, Any]:
    """Manually add a busy block."""
    try:
        engine = get_availability_engine()
        start = datetime.fromisoformat(request.start)
        end = datetime.fromisoformat(request.end)
        engine.add_busy_block(start, end, request.title)
        return {"status": "success", "message": "Busy block added"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/calendar/available")
async def add_available_block(request: AvailableBlockRequest) -> dict[str, Any]:
    """Manually add an available/focus block."""
    try:
        engine = get_availability_engine()
        start = datetime.fromisoformat(request.start)
        end = datetime.fromisoformat(request.end)
        engine.add_available_block(start, end, request.title)
        return {"status": "success", "message": "Available block added"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get("/max-task-hours")
async def get_max_task_hours_endpoint(horizon: str = "today") -> dict[str, Any]:
    """Alias for /max-task-hours."""
    return await get_max_task_hours(horizon)
