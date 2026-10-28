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


# Minutos/día disponibles del owner (default 240 = 28h/sem). El allocation
# y el daily loop reparten ESTE presupuesto; sin persistirlo, el sistema
# planifica con 4h/día aunque el owner disponga de 11h/día.
DEFAULT_DAILY_MINUTES = 240
MIN_DAILY_MINUTES = 30
MAX_DAILY_MINUTES = 960


def _load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {"target_usd": 5000.0, "workspace_active": {}, "daily_minutes": DEFAULT_DAILY_MINUTES}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "target_usd": float(data.get("target_usd", 5000.0)),
            "workspace_active": dict(data.get("workspace_active", {})),
            "daily_minutes": int(data.get("daily_minutes", DEFAULT_DAILY_MINUTES)),
        }
    except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
        logger.warning("mission-hub: unreadable state, using defaults: %s", exc)
        return {"target_usd": 5000.0, "workspace_active": {}, "daily_minutes": DEFAULT_DAILY_MINUTES}


def _save_state(state: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# Brújula PERSONAL_CONTEXT §24: rama del árbol Vida que cada workspace mueve.
_WORKSPACE_TO_LIFE_GOAL: dict[str, str] = {
    "bug_bounty": "Carrera → Bug Bounty",
    "dev_bounty": "Carrera → Software",
    "ai_training": "Carrera → IA",
    "droppinglabel": "Negocios → Droppinglabel",
    "ecommerce": "Negocios → Droppinglabel",
    "mercado_libre": "Negocios → Mercado Libre",
    "meli": "Negocios → Mercado Libre",
    "adriel_webs": "Negocios → Adriel Webs",
    "client_acquisition": "Negocios → Adriel Webs",
    "content_factory": "Negocios",
    "affiliate": "Negocios",
    "lead_services": "Negocios",
    "partnership": "Negocios",
    "knowledge_assets": "Tecnología → OWNEX",
    "trading": "Independencia → Finanzas",
    "capital": "Independencia → Finanzas",
    "investment": "Independencia → Finanzas",
    "asset_factory": "Independencia → Patrimonio",
}


def _life_goal_from_workspace(workspace: str | None) -> str:
    """Workspace id → rama Vida. Matching agnóstico a espacios/guiones."""
    key = (workspace or "").strip().lower().replace(" ", "_").replace("-", "_")
    if key in _WORKSPACE_TO_LIFE_GOAL:
        return _WORKSPACE_TO_LIFE_GOAL[key]
    for ws_id, goal in _WORKSPACE_TO_LIFE_GOAL.items():
        if ws_id and ws_id in key:
            return goal
    return "Independencia → Finanzas"


def _life_goal_for_platform(platform: str | None) -> str:
    """Plataforma → workspace (best-effort) → rama Vida. Nunca vacío."""
    try:
        from cores.automation.kill_scale import _workspace_for_channel

        ws = _workspace_for_channel(platform or "")
        if ws:
            return _life_goal_from_workspace(ws)
    except Exception:
        pass
    return _life_goal_from_workspace(platform)


def _oba_to_next_action(oba: Any) -> dict[str, Any]:
    """OneBestAction (dataclass) → dict actionable. Sin inventar endpoints."""
    import re

    d = oba.to_dict() if hasattr(oba, "to_dict") else dict(oba)
    hours = float(d.get("estimated_human_hours") or 0)
    instr = str(d.get("next_step_instruction") or "").strip()
    m = re.match(r"^(GET|POST|PUT|PATCH|DELETE)\s+\S+", instr)
    return {
        "title": str(d.get("title") or "Siguiente acción"),
        "why": str(d.get("why_now") or ""),
        "est_minutes": int(round(hours * 60)),
        "url": d.get("url"),
        "endpoint": m.group(0) if m else "",
        "life_goal": _life_goal_for_platform(str(d.get("platform") or "")),
    }


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

    # Actionable next_action: SSOT via one_best_action + allocation + feedback (never generic string)
    try:
        from cores.direct_work_engine import one_best_action as oba_mod

        oba = oba_mod.get_one_best_action()
        if oba is None:
            raise ValueError("no oba")
        next_action = _oba_to_next_action(oba)
    except Exception:
        # Fallback: actionable dict from allocation's top slice + checklist
        try:
            from cores.setup.checklist import get_setup_checklist
            from cores.workspaces.allocation import allocate_daily_hours

            chk = get_setup_checklist().status()
            if not chk.get("complete", True) and chk.get("next_task"):
                nt = chk["next_task"]
                next_action = {
                    "title": nt.get("title", "Completar setup"),
                    "why": nt.get("why", ""),
                    "est_minutes": nt.get("est_minutes", 10),
                    "url": nt.get("url") or "/setup/checklist",
                    "endpoint": "GET /setup/checklist",
                    "command": f"Open {nt.get('url') or '/setup/checklist'}",
                }
            else:
                alloc = allocate_daily_hours(60, active={k: bool(v) for k, v in overrides.items()} or None)
                top = alloc.slices[0] if alloc.slices and alloc.slices[0].workspace != "admin" else None
                if top:
                    next_action = {
                        "title": f"Próxima hora: {top.workspace}",
                        "why": top.why,
                        "est_minutes": top.minutes,
                        "url": "/operations/work-queue",
                        "endpoint": "GET /api/mission-hub/allocation/daily",
                        "command": f"Work {top.workspace} {top.minutes}min",
                    }
                else:
                    next_action = {
                        "title": "Define tu primer workspace activo",
                        "why": "Activá un workspace para que OWNEX reparta tu hora",
                        "est_minutes": 5,
                        "url": "/mission",
                        "endpoint": "POST /mission-hub/workspaces/{id}/activate",
                        "command": "POST /mission-hub/workspaces/{id}/activate",
                    }
        except Exception:
            fallback = "Define tu primer workspace activo"
            if active_mix:
                fallback = f"Próxima hora: {active_mix[0]}"
            next_action = {
                "title": fallback,
                "why": "",
                "url": "/mission",
                "endpoint": "GET /mission-hub/overview",
                "command": "GET /mission-hub/overview",
            }

    # Enrich with feedback reallocation hint when available
    try:
        from cores.economic_feedback.engine import build_snapshot

        snap = build_snapshot()
        if snap.reallocation.get("next_hour") and isinstance(next_action, dict):
            # Attach as hint without overriding primary next_action
            next_action["reallocation_hint"] = snap.reallocation
    except Exception:
        pass

    return {
        "mission": mission.to_dict(),
        "levels": levels,
        "workspaces": workspaces,
        "next_action": next_action,
        "target_usd": target,
        "economics": _doctrine_economics(),
        "factory": _factory_snapshot(),
        "money_loop": _money_loop_status(),
    }


def _doctrine_economics() -> dict[str, Any]:
    """Métrica reina en la pantalla diaria: neto/hora-humana + autonomía.

    Best-effort (nunca 500): sin historial → UNKNOWN honesto, jamás inventa.
    """
    try:
        from cores.cycles.metrics import CycleMetricsEngine

        m = CycleMetricsEngine().compute_automation_metrics() or {}
        return {
            "money_per_human_hour": m.get("money_per_human_hour"),
            "automation_ratio": m.get("automation_ratio"),
            "paid_usd": m.get("paid_usd", 0.0),
            "pipeline_usd": m.get("pipeline_usd", 0.0),
            "human_hours": m.get("human_hours"),
        }
    except Exception as exc:
        logger.warning("mission-hub: economics no disponible: %s", exc)
        return {
            "money_per_human_hour": None,
            "automation_ratio": None,
            "paid_usd": 0.0,
            "pipeline_usd": 0.0,
            "human_hours": None,
        }


def _factory_snapshot() -> dict[str, Any]:
    """APP FACTORY en la pantalla diaria: NEXA vs FOCUS. Best-effort, nunca 500."""
    try:
        from cores.app_factory.experiments import get_overview

        full = get_overview()
        exps = full.get("experiments", {})
        return {
            exp: {
                "demand_score": data.get("demand_score"),
                "verdict": data.get("verdict"),
                "views": (data.get("counts") or {}).get("landing_view", 0),
                "plans": (data.get("counts") or {}).get("plan_generated", 0),
                "saves": (data.get("counts") or {}).get("plan_saved", 0),
                "emails": data.get("emails", 0),
            }
            for exp, data in exps.items()
        }
    except Exception as exc:
        logger.warning("mission-hub: factory no disponible: %s", exc)
        return {}


def _money_loop_status() -> dict[str, Any]:
    """Monitor único del loop de dinero: etapas + validaciones + funnel.

    Todo best-effort (nunca 500): cada bloque que falle queda en UNKNOWN/0.
    El humano monitorea acá y valida en /system/review.
    """
    stages: dict[str, Any] = {"targets_active": 0, "findings": {}, "reports": {}}
    try:
        from sqlalchemy import func

        from database import db, models

        session = db.SessionLocal()
        try:
            stages["targets_active"] = (
                session.query(func.count(models.Target.id)).filter(models.Target.active.is_(True)).scalar() or 0
            )
            for status, count in (
                session.query(models.Finding.status, func.count(models.Finding.id))
                .group_by(models.Finding.status)
                .all()
            ):
                stages["findings"][str(status or "unknown")] = int(count or 0)
            for status, count in (
                session.query(models.Report.status, func.count(models.Report.id)).group_by(models.Report.status).all()
            ):
                stages["reports"][str(status or "unknown")] = int(count or 0)
        finally:
            session.close()
    except Exception as exc:
        logger.warning("mission-hub: money_loop stages no disponibles: %s", exc)

    pending: dict[str, Any] = {"total": 0, "counts": {}, "top": None}
    try:
        from cores.review_queue import build_review_queue

        queue = build_review_queue(limit=50)
        data = queue.to_dict()
        pending = {
            "total": data.get("total_items", 0),
            "counts": data.get("counts", {}),
            "top": next(
                (
                    {"label": i.get("label"), "reason": i.get("reason")}
                    for i in (
                        data.get("high_confidence", [])
                        or data.get("medium_confidence", [])
                        or data.get("low_confidence", [])
                    )[:1]
                ),
                None,
            ),
        }
    except Exception as exc:
        logger.warning("mission-hub: money_loop pending no disponible: %s", exc)

    funnel: dict[str, Any] = {
        "outcomes": 0,
        "paid": 0,
        "net_usd": 0.0,
        "net_per_hour": None,
        "as_of": None,
        "state": "UNKNOWN",
    }
    try:
        from cores.economic_feedback.engine import load_snapshot

        snap = load_snapshot()
        if snap:
            funnel = {
                "outcomes": snap.get("total_outcomes", 0),
                "paid": snap.get("total_paid", 0),
                "net_usd": snap.get("total_net", 0.0),
                "net_per_hour": snap.get("global_net_per_hour"),
                "as_of": snap.get("generated_at"),
                "state": "MEASURED" if (snap.get("total_outcomes") or 0) > 0 else "UNKNOWN",
            }
    except Exception as exc:
        logger.warning("mission-hub: money_loop funnel no disponible: %s", exc)

    return {"stages": stages, "pending_validations": pending, "funnel": funnel}


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


class DailyMinutesIn(BaseModel):
    daily_minutes: int = Field(ge=MIN_DAILY_MINUTES, le=MAX_DAILY_MINUTES)


@router.post("/daily-minutes")
async def set_daily_minutes(payload: DailyMinutesIn) -> dict[str, Any]:
    """Persistir capacidad diaria del owner (min/día). Reversible, humano."""
    state = _load_state()
    state["daily_minutes"] = int(payload.daily_minutes)
    try:
        _save_state(state)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"cannot persist daily_minutes: {exc}") from exc
    return {"success": True, "daily_minutes": state["daily_minutes"]}


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


@router.get("/economics")
async def workspace_economics() -> dict[str, Any]:
    """Per-workspace economics from ledger PAID (UNKNOWN until outcomes)."""
    from cores.workspaces.economics import rank_workspaces

    state = _load_state()
    overrides = state.get("workspace_active", {})
    ranked = rank_workspaces(active={k: bool(v) for k, v in overrides.items()} or None)
    return {"workspaces": [e.to_dict() for e in ranked]}


@router.get("/allocation/daily")
async def daily_allocation(total_minutes: int | None = None) -> dict[str, Any]:
    """Today's hour allocation across workspaces (measured or cold-start).

    Sin total_minutes explícito usa la capacidad persistida del owner
    (default 240 min/día). Clamp 30..960 como el resto del sistema.
    """
    from cores.workspaces.allocation import allocate_daily_hours

    state = _load_state()
    overrides = state.get("workspace_active", {})
    if total_minutes is None:
        try:
            total_minutes = int(state.get("daily_minutes", DEFAULT_DAILY_MINUTES))
        except (TypeError, ValueError):
            total_minutes = DEFAULT_DAILY_MINUTES
    alloc = allocate_daily_hours(
        max(30, min(total_minutes, 960)), active={k: bool(v) for k, v in overrides.items()} or None
    )
    return alloc.to_dict()


@router.post("/daily-loop/run")
async def run_daily_loop_endpoint(total_minutes: int = 240) -> dict[str, Any]:
    """Run one daily loop pass (auto rungs execute, gated park with evidence)."""
    from cores.automation.daily_loop import run_daily_loop

    return run_daily_loop(max(30, min(total_minutes, 960))).to_dict()
    from cores.automation.daily_loop import run_daily_loop

    return run_daily_loop(max(30, min(total_minutes, 960))).to_dict()


@router.get("/economic-loop")
async def economic_loop_state() -> dict[str, Any]:
    """Current economic phase from ledger + plan (read-only)."""
    from cores.automation.economic_loop import current_phase

    return current_phase().to_dict()


@router.get("/supervisor")
async def supervisor_console() -> dict[str, Any]:
    """Supervisor console: monitor + validate in ONE call. Read-only, never 500s.

    Junta money_loop (overview) + cola de review con factores (system/review)
    + digest diario + next_action. Aprobar sigue en cada endpoint con su
    Human Gate; acá solo se mira y se decide.
    """
    from datetime import UTC, datetime

    out: dict[str, Any] = {"generated_at": datetime.now(UTC).isoformat()}

    try:
        out["money_loop"] = _money_loop_status()
    except Exception as exc:
        out["money_loop"] = {"error": str(exc)[:200]}

    try:
        from cores.review_queue import build_review_queue

        out["review_queue"] = build_review_queue(limit=20).to_dict()
    except Exception as exc:
        out["review_queue"] = {"error": str(exc)[:200]}

    try:
        from api.routers.daily_digest import daily_digest

        out["digest"] = await daily_digest()
    except Exception as exc:
        out["digest"] = {"error": str(exc)[:200]}

    try:
        from cores.direct_work_engine import one_best_action as oba_mod

        oba = oba_mod.get_one_best_action()
        out["next_action"] = _oba_to_next_action(oba) if oba is not None else {"title": "Sin acción"}
    except Exception as exc:
        out["next_action"] = {"title": "Sin acción", "error": str(exc)[:200]}

    return out
