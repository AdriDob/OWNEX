"""OWNEX Decision Engine — API entry point to say NO.

Wraps the existing ``DecisionEngine`` (cores/decision_core) behind a simple
endpoint so any part of the daily flow can ask "is this task worth it?" —
makes money? loses time? consumes resources? is there a better alternative?

Golden Rule: this router only *exposes* the existing engine, it does not
reimplement decision logic.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from cores.decision_core import create_decision_engine
from cores.knowledge_core import TaskType

logger = logging.getLogger("ownex.api.decision")

router = APIRouter(prefix="/decision", tags=["decision"])

_TASK_TYPE_MAP: dict[str, TaskType] = {
    "recon": TaskType.RECON,
    "scan": TaskType.SCAN,
    "exploit": TaskType.EXPLOIT,
    "report": TaskType.REPORT,
    "research": TaskType.RESEARCH,
    "development": TaskType.DEVELOPMENT,
    "admin": TaskType.ADMIN,
    "opportunity": TaskType.RESEARCH,
    "implementation": TaskType.DEVELOPMENT,
    "learning": TaskType.RESEARCH,
}


class TaskInput(BaseModel):
    task_id: str
    task_type: str = "opportunity"  # opportunity | implementation | learning | admin
    platform: str = "unknown"
    description: str = ""
    estimated_duration_hours: float = 1.0
    estimated_cost_usd: float = 0.0
    estimated_reward_usd: float = 0.0
    confidence: float = 0.5


class EvaluateRequest(BaseModel):
    task: TaskInput


def _engine():
    return create_decision_engine()


@router.post("/evaluate")
async def evaluate(req: EvaluateRequest) -> dict[str, Any]:
    """Decide whether a task is worth doing right now.

    Returns a clear verdict (worth_it / skip), expected value, ROI, hourly
    rate and a human rationale. Feed it anything from the work bank, daily
    brief or Fiverr gig pipeline before committing effort.
    """
    from cores.operations_core import TaskCandidate

    t = req.task
    task_type_enum = _TASK_TYPE_MAP.get(t.task_type, TaskType.RESEARCH)
    candidate = TaskCandidate(
        task_id=t.task_id,
        task_type=task_type_enum,
        platform=t.platform,
        description=t.description,
        estimated_duration=t.estimated_duration_hours * 3600,
        estimated_cost=t.estimated_cost_usd,
        estimated_reward=t.estimated_reward_usd,
        confidence=t.confidence,
    )
    # Use the engine's pure single-candidate evaluation.
    try:
        ev, conf, details = _engine().evaluate_candidate(candidate, "ownex")
    except Exception as exc:  # pragma: no cover — engine expects its own types
        logger.warning("DecisionEngine evaluate failed (%s); falling back to cand logic", exc)
        details = {}
        ev = candidate.expected_value
        conf = candidate.confidence

    # When the engine has no historical data (zero-count beliefs), EV comes back
    # as 0 or slightly negative (from expected cost with no reward baseline).
    # Fall back to the candidate's own expected value so decisions remain
    # actionable instead of defaulting to SKIP.
    if ev <= 0 or details.get("belief_count", 0) == 0:
        ev = candidate.expected_value
        conf = candidate.confidence or conf

    worth_it = ev > 0 and t.estimated_reward_usd > t.estimated_cost_usd
    return {
        "task_id": t.task_id,
        "platform": t.platform,
        "description": t.description,
        "worth_it": worth_it,
        "verdict": "GO" if worth_it else "SKIP",
        "expected_value_usd": round(ev, 2),
        "expected_roi": round(ev / t.estimated_cost_usd, 2) if t.estimated_cost_usd > 0 else 0.0,
        "expected_rate_usd_per_hour": round(
            ev / t.estimated_duration_hours if t.estimated_duration_hours > 0 else 0.0, 2
        ),
        "confidence": round(conf, 3),
        "rationale": details if isinstance(details, dict) else {"engine": str(details)[:200]},
    }


@router.get("/status")
async def status() -> dict[str, Any]:
    """Decision engine status and historical decision count."""
    engine = _engine()
    return {
        "engine": "DecisionEngine (cores.decision_core)",
        "decisions_made": getattr(engine, "_total_decisions", 0),
        "beliefs": len(getattr(engine, "_beliefs", {})),
        "advice": "Evalúa cualquier tarea antes de invertir tiempo o recursos.",
    }
