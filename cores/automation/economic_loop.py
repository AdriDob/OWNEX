"""Economic Loop — DISCOVER→WORK→DELIVER→EARN→COLLECT→SAVE→INVEST→LEARN→SCALE.

Phase tracker over the money lifecycle. Reads the Revenue Ledger + march2027
plan + workspace economics; reports current phase, next transition and the
scale question ("how does this manual activity become a scalable asset?").
Read-only: transitions happen in the ledger, this loop only observes + advises.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("ownex.automation.economic_loop")

PHASES = ("DISCOVER", "WORK", "DELIVER", "EARN", "COLLECT", "SAVE", "INVEST", "LEARN", "SCALE")


@dataclass
class EconomicLoopState:
    phase: str
    evidence: dict[str, Any] = field(default_factory=dict)
    next_transition: str = ""
    scale_question: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "evidence": self.evidence,
            "next_transition": self.next_transition,
            "scale_question": self.scale_question,
            "phases": list(PHASES),
        }


def current_phase() -> EconomicLoopState:
    """Derive the current economic phase from ledger + plan (best-effort)."""
    evidence: dict[str, Any] = {}
    try:
        from cores.revenue.ledger import get_revenue_ledger

        ledger = get_revenue_ledger()
        summary = ledger.get_summary() if hasattr(ledger, "get_summary") else {}
        evidence["ledger_summary"] = summary if isinstance(summary, dict) else {}
        paid = ledger.get_paid_entries()
        evidence["paid_count"] = len(paid)
    except Exception as exc:  # noqa: BLE001
        evidence["ledger_error"] = str(exc)
        evidence["paid_count"] = 0
    try:
        from cores.first_money.tracker import get_first_money_tracker

        plan = get_first_money_tracker().get_march2027_plan()
        evidence["earned_usd"] = plan.get("current_earned", 0)
        evidence["gap_50k"] = plan.get("gap_usd", 50000)
    except Exception:
        evidence["earned_usd"] = 0

    paid_n = int(evidence.get("paid_count", 0) or 0)
    earned = float(evidence.get("earned_usd", 0) or 0)
    if paid_n <= 0 and earned <= 0:
        phase, nxt = "DISCOVER", "First PAID moves DISCOVER→EARN"
    elif paid_n < 3:
        phase, nxt = "EARN", "3+ PAID unlocks repeatability signal"
    elif paid_n < 10:
        phase, nxt = "COLLECT", "10+ outcomes unlock channel statistics"
    else:
        phase, nxt = "LEARN", "30-50 outcomes unlock meaningful planning"
    return EconomicLoopState(
        phase=phase,
        evidence=evidence,
        next_transition=nxt,
        scale_question="¿Cómo convierto esta actividad manual en un activo escalable (template/producto/recurring)?",
    )
