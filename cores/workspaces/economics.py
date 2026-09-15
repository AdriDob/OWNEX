"""Workspace Economics — EV/h per workspace from real outcomes only.

SSOT for answering "which workspace deserves my time today?". Reuses:
- policies.allowed_in_income_mix / rank_for_mission (who may join the mix)
- channel_economy() (personal per-channel table, UNKNOWN until 1 paid)
- compute_expected_human_value() ($/h-human + cash speed)

Never invents: no outcomes → UNKNOWN economics, honesty preserved.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from cores.workspaces.policies import allowed_in_income_mix, income_role
from cores.workspaces.registry import WorkspaceType

logger = logging.getLogger("ownex.workspaces.economics")


@dataclass
class WorkspaceEconomics:
    workspace: str
    role: str
    eligible: bool
    expected_net_usd: float | None = None  # None = UNKNOWN
    p_cash: float | None = None
    ev_per_hour: float | None = None
    repeatability: str = "UNKNOWN"  # REPEATABLE / NON_REPEATABLE / UNKNOWN
    outcomes: int = 0
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "role": self.role,
            "eligible": self.eligible,
            "expected_net_usd": self.expected_net_usd,
            "p_cash": self.p_cash,
            "ev_per_hour": self.ev_per_hour,
            "repeatability": self.repeatability,
            "outcomes": self.outcomes,
            "note": self.note,
        }


def _channel_table() -> dict[str, dict[str, Any]]:
    """Personal per-workspace economics from the Revenue Ledger (PAID-only cash).

    Returns {workspace: {outcomes, net_cash_usd, ...}}. Empty when no PAID
    entries exist — callers surface UNKNOWN, never invent.
    """
    try:
        from cores.revenue.ledger import RevenueState, get_revenue_ledger

        ledger = get_revenue_ledger()
        paid = ledger.get_by_state(RevenueState.PAID)
        by_ws: dict[str, dict[str, Any]] = {}
        for entry in paid:
            d = entry.to_dict() if hasattr(entry, "to_dict") else entry
            ws = _workspace_for_platform(str(d.get("platform") or ""))
            if not ws:
                continue
            row = by_ws.setdefault(ws, {"outcomes": 0, "net_cash_usd": 0.0})
            row["outcomes"] += 1
            row["net_cash_usd"] = round(row["net_cash_usd"] + float(d.get("net_usd") or 0.0), 2)
        return by_ws
    except Exception:
        return {}


def _workspace_for_platform(platform: str) -> str | None:
    """Map a ledger platform string to a workspace value (best-effort)."""
    p = (platform or "").lower()
    if not p:
        return None
    bug = ("hackerone", "bugcrowd", "intigriti", "yeswehack", "immunefi", "hackenproof", "huntr")
    dev = ("algora", "opire", "issuehunt", "bountyboard", "polar", "gitpay", "github", "dework", "superteam", "gitcoin")
    aiw = ("outlier", "mindrift", "alignerr", "mercor", "dataannotation", "kaggle", "prolific")
    if any(k in p for k in bug):
        return WorkspaceType.BUG_BOUNTY.value
    if any(k in p for k in dev):
        return WorkspaceType.DEV_BOUNTY.value
    if any(k in p for k in aiw):
        return WorkspaceType.AI_TRAINING.value
    if "fiverr" in p or "contra" in p or "workana" in p:
        return WorkspaceType.DEV_BOUNTY.value
    return None


def _feedback_map() -> dict[str, Any]:
    """Workspace → ChannelEconomics from the feedback engine (best-effort)."""
    try:
        from cores.economic_feedback.engine import compute_channel_economics

        # ChannelEconomics is keyed by platform; map to workspace via _workspace_for_platform aggregate
        # Build workspace aggregate from channel economics
        chans = compute_channel_economics()
        # Aggregate per workspace
        ws_agg: dict[str, dict[str, Any]] = {}
        for ch in chans:
            ws = _workspace_for_platform(ch.channel)
            if not ws:
                continue
            a = ws_agg.setdefault(ws, {"paid": 0, "net": 0.0, "hours": 0.0, "p_list": [], "nph_list": []})
            a["paid"] += ch.paid
            a["net"] = round(a["net"] + ch.net_cash, 2)
            if ch.human_hours is not None:
                a["hours"] += ch.human_hours
            if ch.p_cash_real is not None:
                a["p_list"].append(ch.p_cash_real)
            if ch.net_per_hour is not None:
                a["nph_list"].append(ch.net_per_hour)
        # Reduce
        out: dict[str, Any] = {}
        for ws, a in ws_agg.items():
            p_cash = round(sum(a["p_list"]) / len(a["p_list"]), 3) if a["p_list"] else None
            ev_h = (
                round(a["net"] / a["hours"], 2)
                if a["hours"] and a["hours"] > 0
                else (round(sum(a["nph_list"]) / len(a["nph_list"]), 2) if a["nph_list"] else None)
            )
            out[ws] = {
                "paid": a["paid"],
                "net": a["net"],
                "hours": round(a["hours"], 2) if a["hours"] else None,
                "p_cash": p_cash,
                "ev_per_hour": ev_h,
            }
        return out
    except Exception:
        return {}


def economics_for(
    workspace: WorkspaceType | str,
    *,
    active: bool = True,
    include_optional: bool = False,
    allow_last_resort: bool = False,
) -> WorkspaceEconomics:
    """Economics for one workspace from measured outcomes (UNKNOWN when none).

    Now closed-loop: uses economic_feedback (REALIZED NET/H + P(CASH) recalibrado).
    """
    ws = workspace if isinstance(workspace, WorkspaceType) else WorkspaceType(str(workspace))
    role = income_role(ws).value
    eligible = allowed_in_income_mix(
        ws, active=active, include_optional=include_optional, allow_last_resort=allow_last_resort
    )
    if not eligible:
        return WorkspaceEconomics(workspace=ws.value, role=role, eligible=False, note="Fuera del mix por política")

    # Closed-loop map from feedback engine
    fb_map = _feedback_map()
    fb = fb_map.get(ws.value)

    table = _channel_table()
    row = table.get(ws.value, {})

    outcomes = int(row.get("outcomes", 0) or 0)
    # Prefer feedback aggregate; fallback to ledger
    if fb and fb.get("paid", 0) > 0:
        outcomes = int(fb["paid"])
        net = fb.get("net")
        p_cash = fb.get("p_cash")
        ev_h = fb.get("ev_per_hour")
        hours = fb.get("hours")
        # Repeatability from real outcomes count
        repeat = "MEASURED" if outcomes >= 3 else "THIN" if outcomes > 0 else "UNKNOWN"
        note = f"{outcomes} PAID medidos · ${net} neto"
        if ev_h is not None:
            note += f" · ${ev_h}/h realizado"
        if hours is not None:
            note += f" · {hours}h humanas"
        if p_cash is not None:
            note += f" · P(CASH) real {p_cash:.0%}"
        return WorkspaceEconomics(
            workspace=ws.value,
            role=role,
            eligible=True,
            expected_net_usd=float(net) if net is not None else None,
            p_cash=p_cash,
            ev_per_hour=ev_h,
            repeatability=repeat,
            outcomes=outcomes,
            note=note,
        )
    if not row or outcomes <= 0:
        return WorkspaceEconomics(
            workspace=ws.value,
            role=role,
            eligible=True,
            outcomes=0,
            note="Sin PAID medidos — UNKNOWN, no se inventa (primer PAID desbloquea tu P(CASH) real)",
        )
    net = row.get("net_cash_usd")
    return WorkspaceEconomics(
        workspace=ws.value,
        role=role,
        eligible=True,
        expected_net_usd=float(net) if net is not None else None,
        p_cash=None,
        ev_per_hour=None,
        repeatability="UNKNOWN" if outcomes < 3 else "MEASURED",
        outcomes=outcomes,
        note=f"{outcomes} PAID medidos en ledger (sin horas → net/h aún UNKNOWN, registrá human_minutes)",
    )


def rank_workspaces(
    workspaces: list[WorkspaceType | str] | None = None,
    *,
    active: dict[str, bool] | None = None,
    include_optional: bool = False,
    allow_last_resort: bool = False,
) -> list[WorkspaceEconomics]:
    """Rank eligible workspaces by EV/h (UNKNOWN sinks to bottom, never fakes top)."""
    active = active or {}
    wss = list(workspaces) if workspaces else list(WorkspaceType)
    out = [
        economics_for(
            w,
            active=active.get(w.value if isinstance(w, WorkspaceType) else str(w), True),
            include_optional=include_optional,
            allow_last_resort=allow_last_resort,
        )
        for w in wss
    ]
    eligible = [e for e in out if e.eligible]
    eligible.sort(key=lambda e: (e.ev_per_hour is None, -(e.ev_per_hour or 0.0)))
    return eligible
