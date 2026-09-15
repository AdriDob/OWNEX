"""Daily Workspace Allocation — distribute today's hours across workspaces by economics.

No hardcoding: allocation derives from rank_workspaces() (ledger PAID outcomes)
with a cold-start fallback (PRIMARY first, time-capped) while outcomes are UNKNOWN.
Output: per-workspace minutes + expected role + rationale. Pure function, no DB.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from cores.workspaces.economics import rank_workspaces
from cores.workspaces.registry import WorkspaceType

logger = logging.getLogger("ownex.workspaces.allocation")

# Cold-start shares (fraction of available minutes) while economics are UNKNOWN.
# PRIMARY engines split evenly; UPSIDE only with explicit opt-in (never by default).
_COLD_START_PRIMARY = (WorkspaceType.BUG_BOUNTY, WorkspaceType.DEV_BOUNTY, WorkspaceType.AI_TRAINING)
_ADMIN_RESERVE = 0.05  # 5% admin always


@dataclass
class WorkspaceSlice:
    workspace: str
    minutes: int
    share: float
    why: str
    ev_per_hour: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "minutes": self.minutes,
            "share": round(self.share, 3),
            "why": self.why,
            "ev_per_hour": self.ev_per_hour,
        }


@dataclass
class DailyAllocation:
    total_minutes: int
    slices: list[WorkspaceSlice] = field(default_factory=list)
    mode: str = "cold_start"  # cold_start | measured
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_minutes": self.total_minutes,
            "mode": self.mode,
            "note": self.note,
            "slices": [s.to_dict() for s in self.slices],
        }


def allocate_daily_hours(
    total_minutes: int = 240,
    *,
    active: dict[str, bool] | None = None,
    include_optional: bool = False,
    allow_last_resort: bool = False,
) -> DailyAllocation:
    """Allocate today's minutes across eligible workspaces.

    Measured mode (any workspace with PAID outcomes): weight by outcomes share.
    Cold-start mode (zero outcomes everywhere): split PRIMARY evenly, 5% admin.
    """
    ranked = rank_workspaces(active=active, include_optional=include_optional, allow_last_resort=allow_last_resort)
    if not ranked:
        return DailyAllocation(total_minutes=total_minutes, mode="cold_start", note="Sin workspaces elegibles")

    # Feedback-aware measured: weight by REALIZED net/h when available, else by outcomes
    measured = [e for e in ranked if e.outcomes > 0]
    alloc = DailyAllocation(total_minutes=total_minutes)
    productive = int(total_minutes * (1.0 - _ADMIN_RESERVE))

    if measured:
        # Use ev_per_hour (net/h realizado) if any workspace has it; else fallback to outcomes
        has_ev = any(e.ev_per_hour is not None and e.ev_per_hour > 0 for e in measured)
        if has_ev:
            # Weight by ev_per_hour (normalized); floor 10% to keep diversity, PAUSE logic handled in economics feedback
            weights = []
            for e in measured:
                w = float(e.ev_per_hour) if e.ev_per_hour and e.ev_per_hour > 0 else 0.5  # minimal weight if UNKNOWN
                weights.append(max(w, 0.5))
            total_w = sum(weights) or 1.0
            alloc.mode = "measured"
            alloc.note = f"{len(measured)} workspace(s) con PAID medidos; reparto por $/h realizado (net/h)"
            assigned = 0
            for i, e in enumerate(measured):
                share = weights[i] / total_w
                mins = productive // len(measured) if i == len(measured) - 1 else int(productive * share)
                assigned += mins
                why = (
                    f"{e.outcomes} PAID · ${e.ev_per_hour}/h realizado"
                    if e.ev_per_hour is not None
                    else f"{e.outcomes} PAID (sin horas → peso por outcomes)"
                )
                alloc.slices.append(
                    WorkspaceSlice(
                        workspace=e.workspace,
                        minutes=mins,
                        share=share,
                        why=why,
                        ev_per_hour=e.ev_per_hour,
                    )
                )
            if alloc.slices:
                alloc.slices[-1].minutes += productive - assigned
        else:
            total_out = sum(e.outcomes for e in measured)
            alloc.mode = "measured"
            alloc.note = f"{len(measured)} workspace(s) con PAID medidos; resto en pausa hasta evidencia"
            assigned = 0
            for i, e in enumerate(measured):
                share = e.outcomes / total_out if total_out else 1.0 / len(measured)
                mins = productive // len(measured) if i == len(measured) - 1 else int(productive * share)
                assigned += mins
                alloc.slices.append(
                    WorkspaceSlice(
                        workspace=e.workspace,
                        minutes=mins,
                        share=share,
                        why=f"{e.outcomes} PAID medidos (registrá horas para $/h real)",
                        ev_per_hour=e.ev_per_hour,
                    )
                )
            if alloc.slices:
                alloc.slices[-1].minutes += productive - assigned
    else:
        primaries = [e for e in ranked if e.role == "primary"]
        if not primaries:
            primaries = ranked[:3]
        alloc.mode = "cold_start"
        alloc.note = "Sin PAID medidos: reparto parejo en motores PRIMARY hasta evidencia"
        per = productive // len(primaries) if primaries else productive
        assigned = 0
        for i, e in enumerate(primaries):
            mins = productive - assigned if i == len(primaries) - 1 else per
            assigned += mins
            alloc.slices.append(
                WorkspaceSlice(
                    workspace=e.workspace,
                    minutes=mins,
                    share=round(mins / productive, 3) if productive else 0.0,
                    why="Cold-start: PRIMARY parejo hasta primer PAID",
                    ev_per_hour=None,
                )
            )

    alloc.slices.append(
        WorkspaceSlice(
            workspace="admin",
            minutes=total_minutes - productive,
            share=_ADMIN_RESERVE,
            why="Reserva admin: ledger, digest, review",
            ev_per_hour=None,
        )
    )
    return alloc
