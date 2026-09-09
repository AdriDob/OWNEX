"""Execution Engine API — manage and monitor the execution queue."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from cores.execution_engine import get_execution_engine
from cores.execution_queue import ExecState

router = APIRouter(prefix="/api/execution", tags=["execution"])


@router.get("/status")
async def execution_status() -> dict[str, Any]:
    """Get execution engine status and queue statistics."""
    engine = get_execution_engine()
    return engine.get_stats()


@router.post("/start")
async def start_engine() -> dict[str, Any]:
    """Start the execution engine loop."""
    engine = get_execution_engine()
    await engine.start()
    return {"success": True, "status": "started"}


@router.post("/stop")
async def stop_engine() -> dict[str, Any]:
    """Stop the execution engine loop."""
    engine = get_execution_engine()
    await engine.stop()
    return {"success": True, "status": "stopped"}


@router.get("/queue")
async def list_queue(state: str | None = None) -> dict[str, Any]:
    """List queue items, optionally filtered by state."""
    engine = get_execution_engine()
    queue = engine.queue

    if state:
        try:
            target_state = ExecState(state)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid state: {state}")
        item_ids = queue.pending_by_state(target_state.value)
    else:
        item_ids = list(queue._items.keys())

    items = []
    for item_id in item_ids:
        item = queue.get(item_id)
        if item:
            items.append({"item_id": item_id, **item})

    return {"items": items, "count": len(items)}


@router.get("/queue/{item_id}")
async def get_queue_item(item_id: str) -> dict[str, Any]:
    """Get a specific queue item by ID."""
    engine = get_execution_engine()
    item = engine.queue.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item_id": item_id, **item}


@router.post("/queue")
async def submit_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Submit a new job to the execution queue.

    Payload:
    {
        "item_id": "unique-id",  // optional, auto-generated if missing
        "platform": "opire",      // required: opire, issuehunt, algora, etc.
        "action": "execute",      // action to execute
        "payload": {...},         // action-specific parameters
        "max_retries": 3          // optional
    }
    """
    import uuid

    engine = get_execution_engine()

    item_id = payload.get("item_id") or str(uuid.uuid4())
    platform = payload.get("platform")
    action = payload.get("action", "execute")
    job_payload = payload.get("payload", {})
    max_retries = payload.get("max_retries", 3)

    if not platform:
        raise HTTPException(status_code=400, detail="platform is required")

    result = engine.submit_job(
        item_id,
        platform,
        action,
        {
            **job_payload,
            "max_retries": max_retries,
        },
    )
    return {"success": True, "item_id": item_id, "state": result["state"]}


@router.post("/queue/{item_id}/approve")
async def approve_human_step(item_id: str) -> dict[str, Any]:
    """Approve a WAITING_HUMAN item to proceed to SUBMITTED."""
    engine = get_execution_engine()
    try:
        result = engine.approve_human_step(item_id)
        return {"success": True, "item_id": item_id, "new_state": result["state"]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/queue/{item_id}/reject")
async def reject_human_step(item_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Reject a WAITING_HUMAN item."""
    engine = get_execution_engine()
    reason = (payload or {}).get("reason", "rejected")
    try:
        result = engine.reject_human_step(item_id, reason)
        return {"success": True, "item_id": item_id, "new_state": result["state"]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/queue/{item_id}/retry")
async def retry_failed_item(item_id: str) -> dict[str, Any]:
    """Retry a FAILED or DEAD_LETTER item (resets retry count)."""
    engine = get_execution_engine()
    item = engine.queue.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    current_state = ExecState(item["state"])
    if current_state not in (ExecState.FAILED, ExecState.DEAD_LETTER):
        raise HTTPException(status_code=400, detail=f"Cannot retry item in state {current_state}")

    # Reset and re-queue
    item["state"] = ExecState.QUEUED.value
    item["retry_count"] = 0
    item["last_error"] = None
    engine.queue._save()

    return {"success": True, "item_id": item_id, "new_state": "queued"}


@router.delete("/queue/{item_id}")
async def delete_queue_item(item_id: str) -> dict[str, Any]:
    """Remove an item from the queue entirely."""
    engine = get_execution_engine()
    if item_id not in engine.queue._items:
        raise HTTPException(status_code=404, detail="Item not found")
    del engine.queue._items[item_id]
    engine.queue._save()
    return {"success": True, "item_id": item_id}
