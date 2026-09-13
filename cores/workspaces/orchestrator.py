"""Global economic orchestrator — where to put the next hour.

Compares workspaces WITHOUT merging their funnels: each workspace keeps its
own logic (recommend() for DWE workspaces; explicit quotes for commercial
ones). Ranking inputs are P(CASH), EV/hour and time — UNKNOWN sorts last,
never invented.

Excluded by rule: trading (capital, not income) and backup_income (safety
net, reported separately, never ranked as upside).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("ownex.workspaces.orchestrator")

_RANKED_WORKSPACES = (
    "ownex",
    "bug_bounty",
    "dev_bounty",
    "ai_training",
    "droppinglabel",
    "mercado_libre",
    "adriel_webs",
)


@dataclass(slots=True)
class WorkspaceQuote:
    """Manual/computed quote for a workspace without a recommend() pipeline."""

    workspace_id: str
    p_cash: float | None = None
    ev_per_hour: float | None = None
    time_hours: float | None = None
    time_to_cash_days: float | None = None
    repeatability: str = "UNKNOWN"
    risk: str = "UNKNOWN"
    note: str = ""


@dataclass(slots=True)
class WorkspacePick:
    """Top pick of one workspace, in comparable units."""

    workspace_id: str
    title: str
    p_cash: float | None = None
    ev_per_hour: float | None = None
    time_hours: float | None = None
    time_to_cash_days: float | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def sort_key(self) -> tuple:
        known = self.p_cash is not None
        return (not known, -(self.p_cash or 0.0), -(self.ev_per_hour or 0.0))


def orchestrate(
    opportunities_by_workspace: dict[str, list[Any]] | None = None,
    profile: Any | None = None,
    mode: str = "secure_plus_upside",
    quotes: dict[str, WorkspaceQuote] | None = None,
    limit_per_workspace: int = 3,
) -> dict[str, Any]:
    """Rank workspaces for the next hour of work.

    - DWE workspaces: top pick via IntelligentRecommender (guarded per call).
    - Commercial workspaces: via explicit WorkspaceQuote (no invention).
    - Returns ranked picks + next action + safety-net note. Never raises.
    """
    opportunities_by_workspace = opportunities_by_workspace or {}
    quotes = quotes or {}
    picks: list[WorkspacePick] = []

    try:
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        recommender = IntelligentRecommender()
    except Exception as exc:
        logger.debug("Orchestrator recommender unavailable: %s", exc)
        recommender = None

    for ws_id in _RANKED_WORKSPACES:
        try:
            opps = opportunities_by_workspace.get(ws_id, []) or []
            if opps and recommender is not None and profile is not None:
                ranked = recommender.recommend(opps, profile, limit=1, mode=mode) or []
                if ranked:
                    top = ranked[0]
                    o = top.opportunity if hasattr(top, "opportunity") else top
                    picks.append(
                        WorkspacePick(
                            workspace_id=ws_id,
                            title=str(getattr(o, "title", ws_id)),
                            p_cash=getattr(top, "p_cash", None),
                            ev_per_hour=_ev_hour(o),
                            time_hours=_hours(o),
                            time_to_cash_days=_days(getattr(o, "time_to_payout_days", None)),
                            detail={"ranked_id": str(getattr(o, "id", ""))},
                        )
                    )
                    continue
            quote = quotes.get(ws_id)
            if quote is not None:
                picks.append(
                    WorkspacePick(
                        workspace_id=ws_id,
                        title=quote.note or ws_id,
                        p_cash=quote.p_cash,
                        ev_per_hour=quote.ev_per_hour,
                        time_hours=quote.time_hours,
                        time_to_cash_days=quote.time_to_cash_days,
                        detail={"repeatability": quote.repeatability, "risk": quote.risk},
                    )
                )
        except Exception as exc:
            logger.debug("Orchestrator workspace %s skipped: %s", ws_id, exc)

    picks.sort(key=lambda p: p.sort_key())
    top = picks[0] if picks else None
    return {
        "picks": [
            {
                "workspace_id": p.workspace_id,
                "title": p.title,
                "p_cash": p.p_cash,
                "ev_per_hour": p.ev_per_hour,
                "time_hours": p.time_hours,
                "time_to_cash_days": p.time_to_cash_days,
                "detail": p.detail,
            }
            for p in picks
        ],
        "next_action": (
            {
                "workspace_id": top.workspace_id,
                "title": top.title,
                "why": _why(top),
            }
            if top
            else None
        ),
        "safety_net": "backup_income (presencial) surfaces only when online cashflow is weak — check it explicitly, never auto-ranked as upside.",
        "trading_note": "trading excluded from income ranking by rule (capital only).",
    }


def _ev_hour(o: Any) -> float | None:
    for attr in ("ev_per_hour_usd", "ev_per_hour", "hourly_rate_usd"):
        try:
            val = getattr(o, attr, None)
            if val is not None and float(val) > 0:
                return round(float(val), 2)
        except (TypeError, ValueError):
            continue
    try:
        pay, hours = float(getattr(o, "payment", 0) or 0), float(getattr(o, "estimated_time_hours", 0) or 0)
        if pay > 0 and hours > 0:
            return round(pay / hours, 2)
    except (TypeError, ValueError):
        pass
    return None


def _hours(o: Any) -> float | None:
    try:
        val = getattr(o, "estimated_time_hours", None)
        return float(val) if val is not None and float(val) > 0 else None
    except (TypeError, ValueError):
        return None


def _days(val: Any) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _why(pick: WorkspacePick) -> str:
    if pick.p_cash is None:
        return "Best available estimate; P(CASH) UNKNOWN — verify before committing time."
    return f"P(CASH) {pick.p_cash:.0%}" + (f", EV/h ${pick.ev_per_hour:.0f}" if pick.ev_per_hour else "")
