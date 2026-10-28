"""Automation Ladder A1-A12 — the 12-rung climb from information to optimization.

Every task in OWNEX lives on this ladder. Each rung has: input, process,
output, evidence, failure recovery. OWNEX always pushes a task to the highest
rung that is technically legitimate and safe. Human Gate guards A3+ (irreversible).

Rungs:
  A0 INFORMATION     — discover + understand, read-only, no side effects
  A1 PREPARE         — generate execution plan, draft deliverables, no mutation
  A2 AUTO-RUN        — reversible auto-execution (analysis, cache, tests, sync)
  A3 HUMAN APPROVAL  — propose + evidence + surface, wait for APPROVE/REJECT/EDIT/DEFER
  A4 HUMAN ACTION    — guided manual steps (links, selectors, checklists)
  A5 EXTERNAL BLOCK  — blocked on external dependency, explain + next step
  A6 CONTINUE        — auto-continue after approval (resume pipeline)
  A7 DELIVER         — execute delivery (PR push, submit, publish)
  A8 MONITOR         — poll status, detect completion/failure/deadline
  A9 PAYMENT TRACK   — PENDING→PAID→FEES→NET→RECEIVED, ledger SSOT
  A10 LEARN          — record outcomes, update P(CASH), channel economics, human minutes
  A11 OPTIMIZE       — re-rank, cut losers, double down winners, re-plan
  A6 UNSUPPORTED     — explicitly unsupported, recorded with reason (never silent)

One Source of Truth: this module owns the ladder contract. Callers move tasks
with `advance(task)`; the ladder decides the next legal rung.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.automation.ladder")


class AutomationRung(StrEnum):
    """The 12 rungs + explicit unsupported."""

    A0_INFORMATION = "A0_information"
    A1_PREPARE = "A1_prepare"
    A2_AUTO_RUN = "A2_auto_run"
    A3_HUMAN_APPROVAL = "A3_human_approval"
    A4_HUMAN_ACTION = "A4_human_action"
    A5_EXTERNAL_BLOCK = "A5_external_block"
    A6_CONTINUE = "A6_continue"
    A7_DELIVER = "A7_deliver"
    A8_MONITOR = "A8_monitor"
    A9_PAYMENT = "A9_payment_track"
    A10_LEARN = "A10_learn"
    A11_OPTIMIZE = "A11_optimize"
    A6_UNSUPPORTED = "A6_unsupported"


# Which rungs may run without any human involvement.
AUTO_RUNGS = frozenset({AutomationRung.A0_INFORMATION, AutomationRung.A1_PREPARE, AutomationRung.A2_AUTO_RUN})

# Which rungs require an explicit human decision first.
GATED_RUNGS = frozenset(
    {
        AutomationRung.A3_HUMAN_APPROVAL,
        AutomationRung.A4_HUMAN_ACTION,
        AutomationRung.A7_DELIVER,
        AutomationRung.A9_PAYMENT,
    }
)

_RUNG_LABEL_ES: dict[AutomationRung, str] = {
    AutomationRung.A0_INFORMATION: "A0 · Información",
    AutomationRung.A1_PREPARE: "A1 · Preparar",
    AutomationRung.A2_AUTO_RUN: "A2 · Auto-ejecutar (reversible)",
    AutomationRung.A3_HUMAN_APPROVAL: "A3 · Aprobación humana",
    AutomationRung.A4_HUMAN_ACTION: "A4 · Acción humana guiada",
    AutomationRung.A5_EXTERNAL_BLOCK: "A5 · Bloqueo externo",
    AutomationRung.A6_CONTINUE: "A6 · Continuar",
    AutomationRung.A7_DELIVER: "A7 · Entregar",
    AutomationRung.A8_MONITOR: "A8 · Monitorear",
    AutomationRung.A9_PAYMENT: "A9 · Cobro",
    AutomationRung.A10_LEARN: "A10 · Aprender",
    AutomationRung.A11_OPTIMIZE: "A11 · Optimizar",
    AutomationRung.A6_UNSUPPORTED: "A6 · No soportado",
}

# Default forward transition (happy path). Failures branch to A5/BLOCKED.
_NEXT: dict[AutomationRung, AutomationRung] = {
    AutomationRung.A0_INFORMATION: AutomationRung.A1_PREPARE,
    AutomationRung.A1_PREPARE: AutomationRung.A2_AUTO_RUN,
    AutomationRung.A2_AUTO_RUN: AutomationRung.A3_HUMAN_APPROVAL,
    AutomationRung.A3_HUMAN_APPROVAL: AutomationRung.A6_CONTINUE,
    AutomationRung.A4_HUMAN_ACTION: AutomationRung.A6_CONTINUE,
    AutomationRung.A5_EXTERNAL_BLOCK: AutomationRung.A5_EXTERNAL_BLOCK,  # stays until unblocked
    AutomationRung.A6_CONTINUE: AutomationRung.A7_DELIVER,
    AutomationRung.A7_DELIVER: AutomationRung.A8_MONITOR,
    AutomationRung.A8_MONITOR: AutomationRung.A9_PAYMENT,
    AutomationRung.A9_PAYMENT: AutomationRung.A10_LEARN,
    AutomationRung.A10_LEARN: AutomationRung.A11_OPTIMIZE,
    AutomationRung.A11_OPTIMIZE: AutomationRung.A11_OPTIMIZE,  # terminal: re-plan emits new tasks
    AutomationRung.A6_UNSUPPORTED: AutomationRung.A6_UNSUPPORTED,
}


@dataclass
class LadderTask:
    """A unit of work climbing the ladder."""

    id: str
    title: str
    rung: AutomationRung = AutomationRung.A0_INFORMATION
    payload: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    failure: dict[str, Any] | None = None
    human_minutes: float = 0.0
    automated_minutes: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def needs_human(self) -> bool:
        return self.rung in GATED_RUNGS

    @property
    def is_terminal(self) -> bool:
        return self.rung in (AutomationRung.A11_OPTIMIZE, AutomationRung.A6_UNSUPPORTED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "rung": self.rung.value,
            "rung_label_es": _RUNG_LABEL_ES[self.rung],
            "needs_human": self.needs_human,
            "is_terminal": self.is_terminal,
            "payload": self.payload,
            "evidence": self.evidence,
            "failure": self.failure,
            "human_minutes": self.human_minutes,
            "automated_minutes": self.automated_minutes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def label_es(rung: AutomationRung | str) -> str:
    """Human label for a rung."""
    r = rung if isinstance(rung, AutomationRung) else AutomationRung(str(rung))
    return _RUNG_LABEL_ES[r]


def next_rung(current: AutomationRung | str) -> AutomationRung:
    """Next rung on the happy path (never raises)."""
    r = current if isinstance(current, AutomationRung) else AutomationRung(str(current))
    return _NEXT.get(r, r)


def advance(task: LadderTask, *, to: AutomationRung | str | None = None, evidence: str | None = None) -> LadderTask:
    """Move a task forward (default: happy-path next). Records evidence + timestamp."""
    target = AutomationRung(str(to)) if to is not None else next_rung(task.rung)
    task.rung = target
    task.updated_at = datetime.now(UTC).isoformat()
    if evidence:
        task.evidence.append(evidence)
    logger.info("[LADDER] %s → %s", task.id, target.value)
    return task


def fail(task: LadderTask, *, stage: str, cause: str, impact: str = "", retry: str = "manual") -> LadderTask:
    """Record a failure honestly: never continue faking. Parks on A5 unless unsupported."""
    task.failure = {
        "stage": stage,
        "cause": cause,
        "impact": impact,
        "retry": retry,
        "at": datetime.now(UTC).isoformat(),
    }
    task.rung = AutomationRung.A5_EXTERNAL_BLOCK
    task.updated_at = datetime.now(UTC).isoformat()
    logger.warning("[LADDER] %s FAILED at %s: %s", task.id, stage, cause)
    return task


def mark_unsupported(task: LadderTask, *, reason: str) -> LadderTask:
    """Explicitly unsupported — recorded, never silent."""
    task.failure = {"stage": "classify", "cause": reason, "impact": "out of scope", "retry": "none"}
    task.rung = AutomationRung.A6_UNSUPPORTED
    task.updated_at = datetime.now(UTC).isoformat()
    return task


def automation_ratio(tasks: list[LadderTask]) -> dict[str, Any]:
    """AUTOMATED_WORK / TOTAL_WORK across tasks (minutes-based)."""
    auto = sum(t.automated_minutes for t in tasks)
    human = sum(t.human_minutes for t in tasks)
    total = auto + human
    return {
        "automated_minutes": round(auto, 1),
        "human_minutes": round(human, 1),
        "automation_ratio": round(auto / total, 3) if total > 0 else 0.0,
        "tasks": len(tasks),
    }
