"""Daily Companion System — the daily-use personal operating system layer.

Combines system health, personal state, market opportunities and focus
recommendations into a single daily routine. Answers the spec's core
question every morning:

  What should I do today?
  What opportunities exist?
  What tasks matter most?
  What can be automated?
  What requires my attention?
  What creates the highest value?

All data is read from existing engines (Regla de Oro: no crea datos,
consolida). No LLM, no invented numbers.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.direct_work_engine.daily_companion")


def _safe(fn: Any, fallback: Any = None) -> Any:
    try:
        return fn()
    except Exception as exc:
        logger.debug("Daily companion block degraded: %s", exc)
        return fallback


def daily_companion(
    work_income_usd_per_month: float = 0.0,
    savings_usd_per_month: float = 0.0,
    start_capital_usd: float = 0.0,
    annual_return_rate: float = 0.10,
    target_monthly_usd: float = 100_000.0,
) -> dict[str, Any]:
    """Run the full daily companion routine and return the consolidated briefing.

    Steps:
    1. System state (health score, uptime)
    2. Personal state (objectives, pending tasks, learning goals)
    3. Market state (new opportunities, top sources)
    4. Focus check (what to stop, automate, delegate, improve)
    5. Daily briefing (consolidated summary)
    """
    system = _safe(_system_state, {"status": "unknown", "score": 0})
    personal = _safe(_personal_state, {"objectives": [], "pending_tasks": 0, "learning_goals": []})
    market = _safe(_market_state, {"opportunities": 0, "top_sources": [], "new_ecosystems": 0})
    focus = _safe(_focus_check, {"stop": [], "automate": [], "delegate": [], "improve": []})
    setup = _safe(_setup_progress, {"complete_pct": 0, "complete": False, "next_task": None})
    briefing = _daily_briefing(system, personal, market, focus)
    projection = _safe(
        lambda: _projection(
            work_income_usd_per_month, savings_usd_per_month, start_capital_usd, annual_return_rate, target_monthly_usd
        ),
        {"crossing_months": None, "months_to_target": None, "note": "Configurá ingreso/ahorro para ver tiempos."},
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "system": system,
        "personal": personal,
        "market": market,
        "focus": focus,
        "setup": setup,
        "briefing": briefing,
        "projection": projection,
    }


def _system_state() -> dict[str, Any]:
    from core.health.engine import HealthCenter

    center = HealthCenter()
    status = center.status()
    return {
        "status": status.get("current_status", "unknown"),
        "score": status.get("current_score", 0),
        "running": status.get("running", False),
        "snapshots": status.get("snapshots", 0),
    }


def _personal_state() -> dict[str, Any]:
    from cores.direct_work_engine.workbank import get_workbank

    bank = get_workbank()
    items = list(bank._items.values()) if hasattr(bank, "_items") else []
    pending = len([i for i in items if getattr(i, "status", "") in ("ready_to_deliver", "needs_access")])
    delivered = len([i for i in items if getattr(i, "status", "") == "delivered"])

    return {
        "pending_tasks": pending,
        "delivered_today": delivered,
        "learning_goals": _learning_goals(bank),
    }


def _learning_goals(bank: Any) -> list[str]:
    goals = []
    if bank.progress().get("monthly", {}).get("achieved", 0) < bank.progress().get("monthly", {}).get("target", 1):
        goals.append("Monthly target not yet reached — prioritize high-EV opportunities")
    return goals


def _market_state() -> dict[str, Any]:
    from cores.direct_work_engine.source_intel import SourceIntelEngine

    engine = SourceIntelEngine()
    report = engine.analyze()
    return {
        "opportunities": report.get("total_curated_sources", 0),
        "top_sources": report.get("sources", [])[:5],
        "new_ecosystems": report.get("new_ecosystems_discovered", 0),
        "recommendation": report.get("best_recommendation", ""),
    }


def _focus_check() -> dict[str, Any]:
    from cores.direct_work_engine.workbank import get_workbank

    bank = get_workbank()
    items = list(bank._items.values()) if hasattr(bank, "_items") else []

    stop = []
    automate = []
    delegate = []
    improve = []

    for item in items:
        category = getattr(item, "category", "")
        barrier = getattr(item, "barrier_level", "LOW")
        if str(barrier).upper() == "HIGH":
            stop.append(f"Skip {item.title or item.id} — high barrier, low ROI")
        if category in ("data_annotation", "microtask"):
            automate.append(f"Automate {item.title or item.id} — repetitive, low skill gap")
        if getattr(item, "needs_access", False):
            delegate.append(f"Delegate setup for {item.title or item.id} — needs manual platform config")
        if getattr(item, "reward", 0.0) and getattr(item, "reward", 0.0) < 50:
            improve.append(f"Improve {item.title or item.id} — reward below $50 threshold")

    return {
        "stop": stop[:5],
        "automate": automate[:5],
        "delegate": delegate[:5],
        "improve": improve[:5],
        "summary": f"{len(stop)} to stop, {len(automate)} to automate, {len(delegate)} to delegate, {len(improve)} to improve",
    }


def _setup_progress() -> dict[str, Any]:
    """Configuración total: % completo + la tarea de config de hoy (una sola)."""
    from core.setup.checklist import get_setup_checklist

    status = get_setup_checklist().status()
    return {
        "complete_pct": status["complete_pct"],
        "complete": status["complete"],
        "next_task": status["next_task"],
    }


def _daily_briefing(
    system: dict[str, Any],
    personal: dict[str, Any],
    market: dict[str, Any],
    focus: dict[str, Any],
) -> dict[str, Any]:
    return {
        "greeting": _greeting(),
        "system_health": f"{system.get('status', 'unknown').upper()} (score {system.get('score', 0)})",
        "important_tasks": personal.get("pending_tasks", 0),
        "income_opportunities_analyzed": market.get("opportunities", 0),
        "recommended_actions": [
            market.get("recommendation", "No new opportunities today"),
        ]
        + personal.get("learning_goals", []),
        "focus_summary": focus.get("summary", "No focus items"),
        "estimated_time_saved": _estimate_time_saved(focus),
    }


def _greeting() -> str:
    from datetime import datetime as dt

    hour = dt.now(UTC).hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def _estimate_time_saved(focus: dict[str, Any]) -> str:
    total = sum(len(focus.get(k, [])) for k in ("stop", "automate", "delegate", "improve"))
    if total == 0:
        return "0 minutes"
    return f"~{total * 15} minutes"


def _projection(
    work_income_usd_per_month: float,
    savings_usd_per_month: float,
    start_capital_usd: float,
    annual_return_rate: float,
    target_monthly_usd: float,
) -> dict[str, Any]:
    from cores.direct_work_engine.income_projection import project_income

    if work_income_usd_per_month <= 0 and savings_usd_per_month <= 0:
        return {"crossing_months": None, "months_to_target": None, "note": "Configurá ingreso/ahorro para ver tiempos."}
    projection = project_income(
        work_income_usd_per_month=work_income_usd_per_month,
        savings_usd_per_month=savings_usd_per_month,
        start_capital_usd=start_capital_usd,
        annual_return_rate=annual_return_rate,
        target_monthly_usd=target_monthly_usd,
    )
    return {
        "crossing_months": projection.crossing_months,
        "months_to_target": projection.months_to_target,
        "capital_at_target_usd": round(projection.capital_at_target_usd, 2),
        "target_monthly_usd": target_monthly_usd,
    }
