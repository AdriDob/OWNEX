"""Projects API — portfolio, detail, next-actions, task transitions.

Thin adapter over cores.projects.registry (single Project OS engine).
Task state changes here are planning-level; execution keeps using the
ladder/Human Gate path. Never 500s on read paths.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.projects.models import AutomationLevel, ProjectState, ProjectTask, TaskState
from cores.projects.registry import ProjectStore, finance_for, maintenance_due, next_actions, portfolio

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _store() -> ProjectStore:
    return ProjectStore()


class TaskIn(BaseModel):
    phase: str = "operacion"
    title: str
    description: str = ""
    priority: int = 5
    effort_min: int = 30
    automation: str = "manual"
    tool: str = ""
    expected_result: str = ""
    financial_impact_usd: float = 0.0
    urgency: int = 5
    risk: int = 5
    growth: int = 5
    recurring: str | None = None
    depends_on: list[str] = Field(default_factory=list)


class TaskStateIn(BaseModel):
    state: str
    evidence: str = ""


@router.get("")
async def list_projects() -> dict[str, Any]:
    """Portfolio: status/health/progress/revenue/next/blocker per project."""
    try:
        return {"projects": portfolio(_store())}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/next-actions")
async def global_next_actions(limit: int = 3) -> dict[str, Any]:
    """TOP-N actions across ALL projects by priority score."""
    try:
        return {"actions": next_actions(_store(), limit=max(1, min(limit, 10)))}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/maintenance")
async def maintenance() -> dict[str, Any]:
    """Recurring maintenance due across projects."""
    try:
        return {"items": maintenance_due(_store())}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{project_id}")
async def project_detail(project_id: str) -> dict[str, Any]:
    """Project detail: plan + tasks + finance (ledger PAID-only) + health."""
    from cores.projects.models import health_score

    store = _store()
    p = store.get(project_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"unknown project: {project_id}")
    d = p.to_dict(include_tasks=True)
    counts = d["task_counts"]
    d["health"] = health_score(p, blocked=counts.get("blocked", 0))
    d["finance"] = finance_for(project_id)
    return d


@router.post("/{project_id}/state")
async def set_project_state(project_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Transition project state (validated enum, fail-closed 422)."""
    try:
        state = ProjectState(str((body or {}).get("state", "")))
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid project state") from None
    if not _store().set_project_state(project_id, state):
        raise HTTPException(status_code=404, detail=f"unknown project: {project_id}")
    return {"project": project_id, "state": state.value}


@router.post("/{project_id}/tasks")
async def add_task(project_id: str, body: TaskIn) -> dict[str, Any]:
    """Add task (dedup by title+phase → 409)."""
    import hashlib

    store = _store()
    if store.get(project_id) is None:
        raise HTTPException(status_code=404, detail=f"unknown project: {project_id}")
    try:
        automation = AutomationLevel(body.automation)
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid automation level") from None
    tid = f"{project_id}-{body.phase}-{hashlib.sha256(body.title.encode()).hexdigest()[:6]}"
    task = ProjectTask(
        id=tid,
        project_id=project_id,
        phase=body.phase,
        title=body.title,
        description=body.description,
        priority=body.priority,
        effort_min=body.effort_min,
        automation=automation,
        tool=body.tool,
        expected_result=body.expected_result,
        financial_impact_usd=body.financial_impact_usd,
        urgency=body.urgency,
        risk=body.risk,
        growth=body.growth,
        recurring=body.recurring,
        depends_on=body.depends_on,
    )
    if not store.add_task(project_id, task):
        raise HTTPException(status_code=409, detail="duplicate task (same title+phase)")
    return {"task_id": tid, "task": task.to_dict()}


@router.post("/tasks/{task_id}/state")
async def set_task_state(task_id: str, body: TaskStateIn, project: str = "") -> dict[str, Any]:
    """Transition any task (project resolved by ?project= or scan)."""
    try:
        state = TaskState(body.state)
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid task state") from None
    store = _store()
    pid = project
    if not pid:
        for p in store.list():
            if task_id in p.tasks:
                pid = p.id
                break
    if not pid or not store.set_task_state(pid, task_id, state, evidence=body.evidence):
        raise HTTPException(status_code=404, detail=f"unknown task: {task_id}")
    return {"task_id": task_id, "project": pid, "state": state.value}
