"""Hunt API router — autonomous bug bounty pipeline control."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("ownex.api.hunt")
router = APIRouter(prefix="/api/hunt", tags=["hunt"])

# Track background tasks to prevent silent leaks
_hunt_tasks: set[asyncio.Task] = set()

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
    _hunt_state["started_at"] = datetime.now(UTC).isoformat()
    _hunt_state["findings_found"] = 0
    _hunt_state["targets_scanned"] = 0
    logger.info("Hunt started")

    # Kick off an immediate pipeline cycle on the LIVE scheduler instance.
    # Never create a second ScanScheduler here: it would run with empty state
    # (no cooldowns/last_run) and drift from the instance the app actually runs.
    try:
        import asyncio

        from api import scheduler as sched_mod
        from api.scheduler import ScanScheduler

        sched = sched_mod.scheduler_instance
        if sched is None:
            sched = ScanScheduler(interval_minutes=30)
            sched_mod.scheduler_instance = sched
        t = asyncio.create_task(sched.run_cycle())
        _hunt_tasks.add(t)
        t.add_done_callback(_hunt_tasks.discard)
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


@router.post("/restart")
async def restart_hunt():
    """Stop + start in one call (CommandPalette + hunt store contract).

    Added 2026-09-12: frontend called /hunt/restart which 404'd (only
    start/pause/resume/stop existed). Restart = fresh started_at/counters +
    a new pipeline cycle on the LIVE scheduler instance (never a second one).
    """
    _hunt_state["status"] = "idle"
    _hunt_state["started_at"] = None
    return await start_hunt()


class CrewAgentIn(BaseModel):
    agent_id: str = Field(min_length=1, max_length=64)
    name: str = ""
    mode: str = "FAST"
    max_targets: int = Field(default=5, ge=1, le=20)


class CrewAssignIn(BaseModel):
    agent_id: str = Field(min_length=1)
    target: str = Field(min_length=1, max_length=253)


@router.get("/crew")
async def crew_status() -> dict[str, Any]:
    """Crew + métricas por agente. Nunca 500."""
    try:
        from cores.hunt.crew import get_hunt_crew

        crew = get_hunt_crew()
        agents = crew.list_agents()
        return {
            "success": True,
            "agents": [{**a, "stats": crew.agent_stats(a["agent_id"])} for a in agents],
        }
    except Exception as e:
        logger.exception("Crew status failed")
        return {"success": False, "agents": [], "error": str(e)[:200]}


@router.post("/crew/agents")
async def crew_create_agent(payload: CrewAgentIn) -> dict[str, Any]:
    """Crea un hunt agent (organiza cobertura; no escanea solo)."""
    from cores.hunt.crew import get_hunt_crew

    out = get_hunt_crew().create_agent(
        payload.agent_id, name=payload.name, mode=payload.mode, max_targets=payload.max_targets
    )
    if not out.get("ok"):
        raise HTTPException(status_code=422, detail=str(out.get("reason", "invalid")))
    return {"success": True, **out}


@router.post("/crew/assign")
async def crew_assign_target(payload: CrewAssignIn) -> dict[str, Any]:
    """Asigna un target a un agente (valida DNS, cupo, duplicados)."""
    from cores.hunt.crew import get_hunt_crew

    out = get_hunt_crew().assign(payload.agent_id, payload.target)
    if not out.get("ok"):
        raise HTTPException(status_code=422, detail=str(out.get("reason", "invalid")))
    return {"success": True, **out}
