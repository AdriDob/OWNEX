"""Project OS models — one engine, every project is data + rules + templates.

A Project links a Workspace (identity/goals/context) with a PLAN (phases →
tasks), OPERATIONS refs (suppliers/leads/products owned by their modules),
FINANCE view (read-only over the Revenue Ledger), HEALTH and MAINTENANCE.

States (prompt §5/§7, no ambiguous states):
  Project: IDEA→PLANIFICACION→PREPARACION→CONSTRUCCION→LANZAMIENTO→OPERACION→
           CRECIMIENTO→OPTIMIZACION→ESCALADO→MANTENIMIENTO (+PAUSADO/BLOQUEADO/CERRADO)
  Task: BACKLOG→READY→IN_PROGRESS→WAITING→BLOCKED→DONE (+FAILED/CANCELLED/ARCHIVED)

Priority score (prompt §8/§28): impacto×urgencia×facilidad⁻¹×automatización,
unblocked-first. Pure function, no DB.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ProjectState(StrEnum):
    IDEA = "idea"
    PLANIFICACION = "planificacion"
    PREPARACION = "preparacion"
    CONSTRUCCION = "construccion"
    LANZAMIENTO = "lanzamiento"
    OPERACION = "operacion"
    CRECIMIENTO = "crecimiento"
    OPTIMIZACION = "optimizacion"
    ESCALADO = "escalado"
    MANTENIMIENTO = "mantenimiento"
    PAUSADO = "pausado"
    BLOQUEADO = "bloqueado"
    CERRADO = "cerrado"


class TaskState(StrEnum):
    BACKLOG = "backlog"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class AutomationLevel(StrEnum):
    """Prompt §3/§11: A automática, B semiautomática, C manual, D imposible."""

    AUTOMATICA = "automatica"
    SEMIAUTOMATICA = "semiautomatica"
    MANUAL = "manual"
    IMPOSIBLE = "imposible"


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class ProjectTask:
    """One task inside a project plan. Task→Ladder mapping: READY→A1, IN_PROGRESS→A2/A6,
    WAITING→A3, BLOCKED→A5, DONE→A8 (see to_ladder_rung)."""

    id: str
    project_id: str
    phase: str
    title: str
    description: str = ""
    priority: int = 5  # 1-10, human-set base
    state: TaskState = TaskState.BACKLOG
    depends_on: list[str] = field(default_factory=list)
    effort_min: int = 30
    due: str | None = None
    recurring: str | None = None  # "daily" | "weekly" | "monthly" | None
    automation: AutomationLevel = AutomationLevel.MANUAL
    tool: str = ""
    expected_result: str = ""
    evidence: str = ""
    financial_impact_usd: float = 0.0
    urgency: int = 5  # 1-10
    risk: int = 5  # 1-10, higher = riskier
    growth: int = 5  # 1-10 growth potential
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    done_at: str | None = None

    def to_ladder_rung(self) -> str:
        return {
            TaskState.BACKLOG: "A0_information",
            TaskState.READY: "A1_prepare",
            TaskState.IN_PROGRESS: "A2_auto_run",
            TaskState.WAITING: "A3_human_approval",
            TaskState.BLOCKED: "A5_external_block",
            TaskState.DONE: "A8_monitor",
            TaskState.FAILED: "A5_external_block",
            TaskState.CANCELLED: "A6_unsupported",
            TaskState.ARCHIVED: "A11_optimize",
        }[self.state]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "phase": self.phase,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "state": self.state.value,
            "depends_on": self.depends_on,
            "effort_min": self.effort_min,
            "due": self.due,
            "recurring": self.recurring,
            "automation": self.automation.value,
            "tool": self.tool,
            "expected_result": self.expected_result,
            "evidence": self.evidence,
            "financial_impact_usd": self.financial_impact_usd,
            "urgency": self.urgency,
            "risk": self.risk,
            "growth": self.growth,
            "ladder_rung": self.to_ladder_rung(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "done_at": self.done_at,
        }


@dataclass(slots=True)
class ProjectPhase:
    name: str
    goal: str
    order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "goal": self.goal, "order": self.order}


@dataclass(slots=True)
class Project:
    """One project = workspace + plan + ops refs + finance view + health."""

    id: str
    workspace_id: str
    name: str
    description: str = ""
    category: str = ""
    business_model: str = ""
    state: ProjectState = ProjectState.IDEA
    priority: int = 5  # 1-10
    started_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    goals: list[str] = field(default_factory=list)
    financial_goal_usd: float = 0.0
    # Plan
    phases: list[ProjectPhase] = field(default_factory=list)
    tasks: dict[str, ProjectTask] = field(default_factory=dict)
    # Ops refs (owned by their modules, only IDs here)
    supplier_ids: list[str] = field(default_factory=list)
    lead_ids: list[str] = field(default_factory=list)
    product_ids: list[str] = field(default_factory=list)
    urls: dict[str, str] = field(default_factory=dict)
    # Growth + history
    metrics: dict[str, Any] = field(default_factory=dict)
    decisions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self, *, include_tasks: bool = False) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "business_model": self.business_model,
            "state": self.state.value,
            "priority": self.priority,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "goals": self.goals,
            "financial_goal_usd": self.financial_goal_usd,
            "phases": [p.to_dict() for p in self.phases],
            "task_counts": _count_tasks(self.tasks),
            "supplier_ids": self.supplier_ids,
            "lead_ids": self.lead_ids,
            "product_ids": self.product_ids,
            "urls": self.urls,
            "metrics": self.metrics,
        }
        if include_tasks:
            d["tasks"] = [t.to_dict() for t in self.tasks.values()]
        return d


def _count_tasks(tasks: dict[str, ProjectTask]) -> dict[str, int]:
    counts: dict[str, int] = {"total": len(tasks)}
    for t in tasks.values():
        counts[t.state.value] = counts.get(t.state.value, 0) + 1
    return counts


def priority_score(task: ProjectTask, *, blocked: bool = False) -> float:
    """GLOBAL PRIORITY SCORE (prompt §8/§28). Blocked → sinks. Unlockers float.

    score = (financial_impact_norm*0.35 + urgency*0.20 + growth*0.15
             + ease*0.15 + automation*0.15) * 100 - risk_penalty
    ease derives from effort_min (less effort = easier). All inputs 1-10-ish.
    Pure function, deterministic.
    """
    if blocked or task.state in (TaskState.BLOCKED, TaskState.CANCELLED, TaskState.ARCHIVED):
        return 0.0
    fin = min(max(task.financial_impact_usd, 0.0), 10000.0) / 10000.0 * 10.0
    ease = max(1.0, 10.0 - (task.effort_min / 30.0))
    auto = {
        AutomationLevel.AUTOMATICA: 10.0,
        AutomationLevel.SEMIAUTOMATICA: 7.0,
        AutomationLevel.MANUAL: 4.0,
        AutomationLevel.IMPOSIBLE: 1.0,
    }[task.automation]
    score = fin * 0.35 + task.urgency * 0.20 + task.growth * 0.15 + ease * 0.15 + auto * 0.15
    score -= (task.risk - 5.0) * 0.4  # risk above 5 penalizes
    return round(max(0.0, score * 10.0), 1)


def health_score(project: Project, *, overdue: int = 0, blocked: int = 0) -> dict[str, Any]:
    """Project health: HEALTHY/WARNING/CRITICAL/DORMANT + score 0-100.

    Inputs are counts the caller measures (no hidden DB reads → testable).
    """
    counts = _count_tasks(project.tasks)
    total = counts.get("total", 0)
    done = counts.get("done", 0)
    if project.state in (ProjectState.PAUSADO, ProjectState.CERRADO):
        return {"level": "DORMANT", "score": 0, "detail": f"state={project.state.value}"}
    if project.state == ProjectState.BLOQUEADO or blocked > 0:
        return {"level": "CRITICAL", "score": 20, "detail": f"{blocked} blocked"}
    score = 60.0
    if total > 0:
        score += (done / total) * 30.0
    score -= min(overdue * 5.0, 30.0)
    score = round(max(0.0, min(100.0, score)), 1)
    level = "HEALTHY" if score >= 70 else ("WARNING" if score >= 40 else "CRITICAL")
    return {"level": level, "score": score, "detail": f"{done}/{total} done, {overdue} overdue"}
