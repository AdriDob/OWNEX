"""Cycles API — Work Cycle management endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from core.cycles.events import (
    publish_cycle_created,
    publish_cycle_deleted,
    publish_cycle_metrics_updated,
    publish_cycle_status_changed,
    publish_cycle_updated,
)
from core.cycles.schemas import (
    CycleActionResponse,
    CycleCreate,
    CycleMetrics,
    CycleRead,
    CycleUpdate,
)
from core.cycles.service import get_cycle_service

router = APIRouter(prefix="/api/cycles", tags=["cycles"])


@router.get("", response_model=list[CycleRead])
def list_cycles(enabled_only: bool = Query(False)):
    """List all work cycles."""
    service = get_cycle_service()
    cycles = service.list(enabled_only=enabled_only)
    return cycles


@router.get("/metrics", response_model=dict[str, CycleMetrics])
def get_all_cycle_metrics():
    """Get metrics for all cycles."""
    service = get_cycle_service()
    cycles = service.list()
    metrics = {}
    for cycle in cycles:
        m = service.get_metrics(cycle.id)
        metrics[cycle.slug] = {
            "cycle_id": cycle.id,
            "opportunities_found": m.get("opportunities_found", 0),
            "tasks_active": m.get("tasks_active", 0),
            "tasks_completed": m.get("tasks_completed", 0),
            "estimated_value": m.get("estimated_value", 0.0),
            "success_rate": m.get("success_rate", 0.0),
            "last_execution": m.get("last_execution"),
            "next_action": m.get("next_action"),
            "throughput_score": m.get("throughput_score", 0.0),
        }
    return metrics


@router.get("/{cycle_id}", response_model=CycleRead)
def get_cycle(cycle_id: int):
    """Get a single cycle by ID."""
    service = get_cycle_service()
    cycle = service.get(cycle_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    return cycle


@router.get("/slug/{slug}", response_model=CycleRead)
def get_cycle_by_slug(slug: str):
    """Get a single cycle by slug."""
    service = get_cycle_service()
    cycle = service.get_by_slug(slug)
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    return cycle


@router.post("", response_model=CycleActionResponse)
def create_cycle(cycle: CycleCreate):
    """Create a new work cycle."""
    service = get_cycle_service()
    try:
        new_cycle = service.create(cycle.dict())
        publish_cycle_created(new_cycle.id, new_cycle.slug, new_cycle.name)
        return CycleActionResponse(success=True, message="Cycle created", cycle=new_cycle)
    except Exception as e:
        return CycleActionResponse(success=False, message=str(e))


@router.patch("/{cycle_id}", response_model=CycleActionResponse)
def update_cycle(cycle_id: int, cycle: CycleUpdate):
    """Update a work cycle."""
    service = get_cycle_service()
    existing = service.get(cycle_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cycle not found")

    old_status = existing.status
    update_data = cycle.dict(exclude_unset=True)

    try:
        updated = service.update(cycle_id, update_data)
        if updated:
            publish_cycle_updated(updated.id, updated.slug, updated.name)
            if "status" in update_data and update_data["status"] != old_status:
                publish_cycle_status_changed(updated.id, updated.slug, updated.name, old_status, updated.status)
            return CycleActionResponse(success=True, message="Cycle updated", cycle=updated)
        return CycleActionResponse(success=False, message="Cycle not found")
    except Exception as e:
        return CycleActionResponse(success=False, message=str(e))


@router.delete("/{cycle_id}", response_model=CycleActionResponse)
def delete_cycle(cycle_id: int):
    """Delete a work cycle."""
    service = get_cycle_service()
    existing = service.get(cycle_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cycle not found")

    try:
        success = service.delete(cycle_id)
        if success:
            publish_cycle_deleted(cycle_id, existing.slug, existing.name)
            return CycleActionResponse(success=True, message="Cycle deleted")
        return CycleActionResponse(success=False, message="Failed to delete")
    except Exception as e:
        return CycleActionResponse(success=False, message=str(e))


@router.post("/{cycle_id}/activate", response_model=CycleActionResponse)
def activate_cycle(cycle_id: int, next_action: str | None = None):
    """Set cycle to RUNNING status."""
    service = get_cycle_service()
    existing = service.get(cycle_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cycle not found")

    old_status = existing.status
    try:
        activated = service.activate(cycle_id, next_action)
        if activated:
            publish_cycle_status_changed(activated.id, activated.slug, activated.name, old_status, activated.status)
            return CycleActionResponse(success=True, message="Cycle activated", cycle=activated)
        return CycleActionResponse(success=False, message="Cycle not found")
    except Exception as e:
        return CycleActionResponse(success=False, message=str(e))


@router.post("/{cycle_id}/pause", response_model=CycleActionResponse)
def pause_cycle(cycle_id: int):
    """Set cycle to PAUSED status."""
    service = get_cycle_service()
    existing = service.get(cycle_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cycle not found")

    old_status = existing.status
    try:
        paused = service.pause(cycle_id)
        if paused:
            publish_cycle_status_changed(paused.id, paused.slug, paused.name, old_status, paused.status)
            return CycleActionResponse(success=True, message="Cycle paused", cycle=paused)
        return CycleActionResponse(success=False, message="Cycle not found")
    except Exception as e:
        return CycleActionResponse(success=False, message=str(e))


@router.post("/{cycle_id}/complete", response_model=CycleActionResponse)
def complete_cycle(cycle_id: int):
    """Set cycle to COMPLETED status."""
    service = get_cycle_service()
    existing = service.get(cycle_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cycle not found")

    old_status = existing.status
    try:
        completed = service.complete(cycle_id)
        if completed:
            publish_cycle_status_changed(completed.id, completed.slug, completed.name, old_status, completed.status)
            return CycleActionResponse(success=True, message="Cycle completed", cycle=completed)
        return CycleActionResponse(success=False, message="Cycle not found")
    except Exception as e:
        return CycleActionResponse(success=False, message=str(e))


@router.post("/{cycle_id}/error", response_model=CycleActionResponse)
def set_cycle_error(cycle_id: int, error_msg: str):
    """Set cycle to ERROR status with message."""
    service = get_cycle_service()
    existing = service.get(cycle_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cycle not found")

    old_status = existing.status
    try:
        errored = service.set_error(cycle_id, error_msg)
        if errored:
            publish_cycle_status_changed(errored.id, errored.slug, errored.name, old_status, errored.status)
            return CycleActionResponse(success=True, message="Error recorded", cycle=errored)
        return CycleActionResponse(success=False, message="Cycle not found")
    except Exception as e:
        return CycleActionResponse(success=False, message=str(e))


@router.post("/{cycle_id}/metrics", response_model=CycleActionResponse)
def update_cycle_metrics(cycle_id: int, metrics: dict[str, Any]):
    """Update cycle metrics (stored in cycle config)."""
    service = get_cycle_service()
    existing = service.get(cycle_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Cycle not found")

    try:
        updated = service.update_metrics(cycle_id, metrics)
        if updated:
            publish_cycle_metrics_updated(updated.id, updated.slug, updated.name, metrics)
            return CycleActionResponse(success=True, message="Metrics updated", cycle=updated)
        return CycleActionResponse(success=False, message="Cycle not found")
    except Exception as e:
        return CycleActionResponse(success=False, message=str(e))


@router.post("/initialize", response_model=CycleActionResponse)
def initialize_cycles():
    """Force initialization of default cycles."""
    # Access private method to re-seed
    from core.cycles.models import DEFAULT_CYCLES, Base, Cycle
    from core.database.manager import get_db_manager

    mgr = get_db_manager()
    if "cycles" not in mgr.list_databases():
        mgr.register("cycles", "cycles.db")
        mgr.run_migrations("cycles", Base)

    db = mgr.get_session("cycles")
    try:
        existing = db.query(Cycle).count()
        if existing == 0:
            for cycle_data in DEFAULT_CYCLES:
                cycle = Cycle(**cycle_data)
                db.add(cycle)
            db.commit()
            return CycleActionResponse(success=True, message=f"Initialized {len(DEFAULT_CYCLES)} default cycles")
        return CycleActionResponse(success=True, message=f"Cycles already exist ({existing} found)")
    except Exception as exc:
        db.rollback()
        return CycleActionResponse(success=False, message=str(exc))
    finally:
        db.close()
