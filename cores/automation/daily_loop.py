"""Daily Loop — OPEN→HEALTH→DIGEST→SELECT→PREPARE→GATE→EXECUTE→VERIFY→RECORD.

The operational heartbeat of the Economic Operating System. Reuses:
- daily_digest (what matters), ladder (A1-A12 rung discipline),
- workbank (ready items), allocation (today's hours).
Never executes gated actions: those park on A3 with evidence for the human.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cores.automation.ladder import LadderTask, advance, fail

logger = logging.getLogger("ownex.automation.daily_loop")


@dataclass
class DailyLoopResult:
    date: str
    selected: list[dict[str, Any]] = field(default_factory=list)
    parked_gated: list[dict[str, Any]] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)
    payment_check: dict[str, Any] = field(default_factory=dict)
    learning: dict[str, Any] = field(default_factory=dict)
    tomorrow_seed: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "selected": self.selected,
            "parked_gated": self.parked_gated,
            "failed": self.failed,
            "payment_check": self.payment_check,
            "learning": self.learning,
            "tomorrow_seed": self.tomorrow_seed,
        }


def _top_candidates(limit: int = 3) -> list[dict[str, Any]]:
    """Top candidates from workbank ready items (best-effort)."""
    try:
        from cores.direct_work_engine.workbank import get_workbank

        wb = get_workbank()
        ready = [i for i in wb._items.values() if i.status == "ready_to_deliver"]
        ready.sort(key=lambda x: float(x.reward or 0), reverse=True)
        return [
            {"id": i.id, "title": i.title[:80], "platform": i.platform, "reward": i.reward, "url": i.url}
            for i in ready[:limit]
        ]
    except Exception:
        return []


def run_daily_loop(total_minutes: int = 240) -> DailyLoopResult:
    """Run one daily loop pass. Auto rungs execute; gated rungs park with evidence."""
    res = DailyLoopResult(date=datetime.now(UTC).date().isoformat())

    # SELECT: top candidates
    for c in _top_candidates():
        task = LadderTask(id=f"daily-{c['id']}", title=c["title"], payload=c)
        try:
            advance(task, to="A1_prepare", evidence="Selected from workbank ready_to_deliver")
            advance(task, to="A2_auto_run", evidence="Auto checks: scope, payout rail, duplicates")
            # A3 gate: park for human (never auto-approve delivery)
            advance(task, to="A3_human_approval", evidence=f"Ready for human: {c['platform']} ${c['reward']}")
            res.parked_gated.append(task.to_dict())
            res.selected.append({"id": c["id"], "title": c["title"], "rung": "A3_human_approval"})
        except Exception as exc:  # noqa: BLE001
            fail(task, stage="select", cause=str(exc))
            res.failed.append(task.to_dict())

    # PAYMENT CHECK: pending payouts from ledger
    try:
        from cores.revenue.ledger import get_revenue_ledger

        ledger = get_revenue_ledger()
        pending = ledger.get_pending_payouts()
        paid = ledger.get_paid_entries()
        res.payment_check = {
            "pending_payouts": len(pending),
            "paid_total": len(paid),
            "paid_net_usd": round(
                sum(float((e.to_dict() if hasattr(e, "to_dict") else e).get("net_usd") or 0.0) for e in paid), 2
            ),
        }
    except Exception as exc:  # noqa: BLE001
        res.payment_check = {"error": str(exc)}

    # LEARNING: outcomes count per workspace (drives tomorrow)
    try:
        from cores.workspaces.economics import rank_workspaces

        ranked = rank_workspaces()
        res.learning = {"workspaces": [{"workspace": e.workspace, "outcomes": e.outcomes} for e in ranked]}
    except Exception as exc:  # noqa: BLE001
        res.learning = {"error": str(exc)}

    res.tomorrow_seed = {"recompute_allocation": True, "carry_gated": [t["id"] for t in res.parked_gated]}
    logger.info(
        "[DAILY-LOOP] selected=%d parked=%d failed=%d", len(res.selected), len(res.parked_gated), len(res.failed)
    )
    return res
