"""Hunt API router — autonomous bug bounty pipeline control."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

logger = logging.getLogger("catseye.api.hunt")
router = APIRouter(prefix="/api/hunt", tags=["hunt"])

_hunt_state = {
    "status": "idle",
    "started_at": None,
    "findings_found": 0,
    "targets_scanned": 0,
}


@router.get("/status")
async def status():
    return _hunt_state


@router.post("/start")
async def start_hunt():
    if _hunt_state["status"] == "running":
        return {"status": "already_running"}

    _hunt_state["status"] = "running"
    _hunt_state["started_at"] = datetime.now(timezone.utc).isoformat()
    _hunt_state["findings_found"] = 0
    _hunt_state["targets_scanned"] = 0
    logger.info("Hunt started")

    # Kick off immediate pipeline run
    try:
        import asyncio
        from api.scheduler import ScanScheduler

        sched = ScanScheduler(interval_minutes=30)
        asyncio.create_task(sched._run_pipeline())
    except Exception as e:
        logger.warning("Hunt pipeline kickoff failed: %s", e)

    return {"status": "started", "started_at": _hunt_state["started_at"]}


@router.post("/pause")
async def pause_hunt():
    if _hunt_state["status"] != "running":
        return {"status": "not_running"}
    _hunt_state["status"] = "paused"
    logger.info("Hunt paused")
    return {"status": "paused"}


@router.post("/resume")
async def resume_hunt():
    if _hunt_state["status"] != "paused":
        return {"status": "not_paused"}
    _hunt_state["status"] = "running"
    logger.info("Hunt resumed")
    return {"status": "resumed"}


@router.post("/stop")
async def stop_hunt():
    if _hunt_state["status"] == "idle":
        return {"status": "already_idle"}
    _hunt_state["status"] = "idle"
    _hunt_state["started_at"] = None
    logger.info("Hunt stopped")
    return {"status": "stopped"}
