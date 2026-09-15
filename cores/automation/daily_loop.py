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


def _top_candidates(limit: int = 3, *, total_minutes: int = 240) -> list[dict[str, Any]]:
    """Top candidates from workbank ready items, weighted by allocation's ev/h when available."""
    try:
        from cores.direct_work_engine.workbank import get_workbank
        from cores.workspaces.allocation import allocate_daily_hours

        wb = get_workbank()
        ready = [i for i in wb._items.values() if i.status == "ready_to_deliver"]
        if not ready:
            return []
        # Prefer allocation-weighted ordering when economics are MEASURED
        try:
            alloc = allocate_daily_hours(total_minutes)
            # Build workspace → minutes weight
            weight = {s.workspace: s.minutes for s in alloc.slices if s.workspace != "admin"}
            # Sort by weight desc then reward
            ready.sort(
                key=lambda x: (weight.get(str(getattr(x, "platform", "") or "").lower(), 0), float(x.reward or 0)),
                reverse=True,
            )
        except Exception:
            ready.sort(key=lambda x: float(x.reward or 0), reverse=True)
        return [
            {
                "id": i.id,
                "title": i.title[:80],
                "platform": i.platform,
                "reward": i.reward,
                "url": i.url,
                "status": i.status,
            }
            for i in ready[:limit]
        ]
    except Exception:
        return []


def _fallback_candidates(limit: int = 3) -> list[dict[str, Any]]:
    """When workbank is empty: propose next setup/first-money action so the loop never returns empty."""
    try:
        from cores.first_money.tracker import get_first_money_tracker
        from cores.setup.checklist import get_setup_checklist

        chk = get_setup_checklist().status()
        if not chk.get("complete", True) and chk.get("next_task"):
            nt = chk["next_task"]
            return [
                {
                    "id": f"setup-{nt['id']}",
                    "title": nt["title"],
                    "platform": "setup",
                    "reward": 0,
                    "url": nt.get("url") or "/setup/checklist",
                    "status": "setup",
                }
            ]
        fm = get_first_money_tracker().get_next_action()
        if fm:
            return [
                {
                    "id": f"first-money-{fm['action']}",
                    "title": fm["title"],
                    "platform": "first_money",
                    "reward": 0,
                    "url": fm.get("url") or "/operations/first-money",
                    "status": "first_money",
                    "endpoint": fm.get("endpoint"),
                    "est_minutes": fm.get("est_minutes"),
                }
            ]
    except Exception:
        pass
    return []


def _a4_payload(c: dict[str, Any]) -> dict[str, Any]:
    """Human-action payload for A4 (links, selectors, checklist) — never generic."""
    platform = str(c.get("platform") or "").lower()
    mapping = {
        "setup": {
            "url": c.get("url") or "/setup/checklist",
            "selector": "SetupChecklist → Abrir",
            "checklist": [c.get("title", "Completar setup")],
        },
        "first_money": {
            "url": c.get("url") or "/operations/first-money",
            "selector": "FirstMoney → Empezar etapa",
            "checklist": [c.get("title", "Siguiente etapa")],
        },
        "algora": {
            "url": c.get("url") or "https://algora.io",
            "selector": "Algora → Claim → PR",
            "checklist": ["Claim issue", "Clone repo", "Generate fix", "Tests", "PR", "Human approve"],
        },
        "opire": {
            "url": c.get("url") or "https://opire.dev",
            "selector": "Opire → Claim",
            "checklist": ["Claim bounty", "Clone", "Fix", "PR"],
        },
    }
    return mapping.get(
        platform,
        {
            "url": c.get("url") or "/operations/work-queue",
            "selector": "WorkQueue → Preparar → Aprobar",
            "checklist": [f"Entregar {c.get('title', '')} en {platform}"],
        },
    )


def run_daily_loop(total_minutes: int = 240) -> DailyLoopResult:
    """Run one daily loop pass. Auto rungs execute; gated rungs park with evidence. Respects total_minutes and allocation."""
    total_minutes = max(30, min(int(total_minutes or 240), 960))
    res = DailyLoopResult(date=datetime.now(UTC).date().isoformat())

    # SELECT: top candidates (allocation-weighted) with fallback so the user never sees empty
    candidates = _top_candidates(limit=3, total_minutes=total_minutes)
    if not candidates:
        candidates = _fallback_candidates(limit=3)
    for c in candidates:
        task = LadderTask(id=f"daily-{c['id']}", title=c["title"], payload={**c, "total_minutes": total_minutes})
        try:
            advance(
                task,
                to="A1_prepare",
                evidence="Selected from workbank ready_to_deliver or fallback (setup/first-money)",
            )
            advance(task, to="A2_auto_run", evidence="Auto checks: scope, payout rail, duplicates")
            # A3 gate: park for human (never auto-approve delivery)
            advance(
                task,
                to="A3_human_approval",
                evidence=f"Ready for human: {c['platform']} ${c.get('reward', 0)} · {c.get('url', '')}",
            )
            # Emit A4 payload immediately so the user has the click without second fetch
            a4 = _a4_payload(c)
            task.payload["a4_human_action"] = a4
            res.parked_gated.append(task.to_dict())
            res.selected.append(
                {
                    "id": c["id"],
                    "title": c["title"],
                    "rung": "A3_human_approval",
                    "a4": a4,
                    "total_minutes": total_minutes,
                }
            )
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
