"""Mission Hub API — one call for the hunter overview card (L7+L9 backend).

Surfaces together (read-mostly, never raises):
- economic mission ($X this month: target/earned/gap via workspace Mission)
- hunter levels (XP snapshot via cores.levels)
- workspaces (registry + income-role policy + persisted active overrides)

State file (tiny JSON, OWNEX_DATA_DIR/hunter/state.json):
{"target_usd": 5000, "workspace_active": {"content_factory": false}}
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("ownex.api.mission_hub")

router = APIRouter(prefix="/mission-hub", tags=["mission-hub"])


def _state_path() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / "hunter" / "state.json"


def _load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {"target_usd": 5000.0, "workspace_active": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "target_usd": float(data.get("target_usd", 5000.0)),
            "workspace_active": dict(data.get("workspace_active", {})),
        }
    except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
        logger.warning("mission-hub: unreadable state, using defaults: %s", exc)
        return {"target_usd": 5000.0, "workspace_active": {}}


def _save_state(state: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


class TargetIn(BaseModel):
    target_usd: float = Field(gt=0, le=1000000)


class AwardIn(BaseModel):
    event: str
    ref_id: str = ""
    note: str = ""


@router.get("/overview")
async def hunter_overview(target_usd: float | None = None) -> dict[str, Any]:
    """Hunter overview: mission + levels + workspaces + next action. Never 500s."""
    from cores.levels import get_progression_engine
    from cores.workspaces.mission import get_mission
    from cores.workspaces.policies import explain, income_role
    from cores.workspaces.registry import get_workspace_registry

    state = _load_state()
    target = float(target_usd) if target_usd and target_usd > 0 else float(state["target_usd"])
    overrides: dict[str, bool] = state["workspace_active"]

    mission = get_mission(target)
    levels = get_progression_engine().summary()

    workspaces = []
    reg = get_workspace_registry()
    for ctx in reg.list_all():
        ws_id = ctx.workspace_id
        active = bool(overrides.get(ws_id, ctx.active))
        workspaces.append(
            {
                "id": ws_id,
                "name": ctx.name,
                "type": ctx.workspace_type.value,
                "role": income_role(ctx.workspace_type).value,
                "policy": explain(ctx.workspace_type),
                "active": active,
                "priority": ctx.priority,
                "goals": list(ctx.goals),
                "automation_policy": ctx.automation_policy.value,
                "linked": {
                    "tasks": len(ctx.task_ids),
                    "opportunities": len(ctx.opportunity_ids),
                    "revenue": len(ctx.revenue_ids),
                },
            }
        )
    workspaces.sort(key=lambda w: (not w["active"], -w["priority"]))

    active_mix = [w["id"] for w in workspaces if w["active"] and w["role"] in ("primary", "upside")]
    next_action = "Define tu primer workspace activo" if not active_mix else f"Próxima hora: {active_mix[0]}"

    return {
        "mission": mission.to_dict(),
        "levels": levels,
        "workspaces": workspaces,
        "next_action": next_action,
        "target_usd": target,
    }


@router.post("/target")
async def set_target(payload: TargetIn) -> dict[str, Any]:
    """Persist the monthly mission target. Reversible, human-driven."""
    state = _load_state()
    state["target_usd"] = float(payload.target_usd)
    try:
        _save_state(state)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"cannot persist target: {exc}") from exc
    return {"success": True, "target_usd": state["target_usd"]}


@router.post("/award")
async def award_xp(payload: AwardIn) -> dict[str, Any]:
    """Grant XP for a verified event. Unknown events 400 (never invent)."""
    from cores.levels import get_progression_engine

    try:
        rec = get_progression_engine().award(payload.event, ref_id=payload.ref_id, note=payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "event": rec.event, "xp": rec.xp, "total_xp": get_progression_engine().total_xp()}


@router.post("/workspaces/{workspace_id}/activate")
async def activate_workspace(workspace_id: str) -> dict[str, Any]:
    """Activate a workspace (persisted override)."""
    from cores.workspaces.registry import get_workspace_registry

    if get_workspace_registry().get(workspace_id) is None:
        raise HTTPException(status_code=404, detail=f"unknown workspace: {workspace_id}")
    state = _load_state()
    state["workspace_active"][workspace_id] = True
    try:
        _save_state(state)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"cannot persist: {exc}") from exc
    return {"success": True, "workspace_id": workspace_id, "active": True}


@router.post("/workspaces/{workspace_id}/deactivate")
async def deactivate_workspace(workspace_id: str) -> dict[str, Any]:
    """Deactivate a workspace (persisted override)."""
    from cores.workspaces.registry import get_workspace_registry

    if get_workspace_registry().get(workspace_id) is None:
        raise HTTPException(status_code=404, detail=f"unknown workspace: {workspace_id}")
    state = _load_state()
    state["workspace_active"][workspace_id] = False
    try:
        _save_state(state)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"cannot persist: {exc}") from exc
    return {"success": True, "workspace_id": workspace_id, "active": False}
