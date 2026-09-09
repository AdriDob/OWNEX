"""Daily Brief V2 — Actionable Intelligence for the Day.

Enhanced version with HTROI-driven recommendations, Work Room integration,
and actionable intelligence per spec.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from cores.direct_work_engine.economic_engine_v2 import get_economic_engine_v2
from cores.direct_work_engine.economics import compute_htroi
from cores.direct_work_engine.models import OpportunityCategory
from cores.direct_work_engine.workbank import get_workbank

logger = logging.getLogger("ownex.direct_work_engine.daily_brief_v2")


def _safe(fn: Any, fallback: Any = None) -> Any:
    try:
        return fn()
    except Exception as exc:
        logger.debug("Daily brief block degraded: %s", exc)
        return fallback


def daily_brief_v2(
    work_income_usd_per_month: float = 0.0,
    savings_usd_per_month: float = 0.0,
    start_capital_usd: float = 0.0,
    annual_return_rate: float = 0.10,
    target_monthly_usd: float = 100_000.0,
) -> dict[str, Any]:
    """
    Generate the enhanced daily brief with actionable intelligence.

    Returns:
        dict with:
        - greeting
        - system_health
        - today_top_opportunity (HTROI-ranked)
        - work_bank_status
        - ai_activity_summary
        - recommended_focus (HTROI-driven)
        - skill_gap_for_top_opp
        - revenue_snapshot
        - projection
        - ai_activity_summary
    """
    # System health
    system = _safe(_system_state, {"status": "unknown", "score": 0})

    # Work bank status
    work_bank = _safe(_work_bank_status, {"ready": 0, "pending": 0, "needs_access": 0})

    # Top opportunity (HTROI-ranked)
    top_opp = _safe(_top_opportunity, None)

    # Skill gap for top opportunity
    skill_gap = _safe(lambda: _skill_gap_for_top(top_opp), None)

    # AI activity summary
    ai_activity = _safe(_ai_activity_summary, {"completed": 0, "failed": 0, "pending": 0})

    # Recommended focus (HTROI-driven)
    focus = _safe(_recommended_focus, {"primary": "No clear focus", "details": []})

    # Revenue snapshot
    revenue = _safe(_revenue_snapshot, {})

    # Projection
    projection = _safe(
        lambda: _projection(
            work_income_usd_per_month,
            savings_usd_per_month,
            start_capital_usd,
            annual_return_rate,
            target_monthly_usd,
        ),
        {"crossing_months": None, "months_to_target": None, "note": "Configure income/savings for projections"},
    )

    # HTROI for top opportunity
    top_htroi = None
    if top_opp:
        top_htroi = _compute_htroi_for_opportunity(top_opp)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "greeting": _greeting(),
        "system_health": {
            "status": system.get("status", "unknown"),
            "score": system.get("score", 0),
        },
        "today_top_opportunity": top_opp,
        "top_opportunity_htroi": top_htroi,
        "work_bank": work_bank,
        "skill_gap": skill_gap,
        "recommended_focus": focus,
        "revenue_snapshot": revenue,
        "projection": projection,
        "ai_activity": ai_activity,
    }


def _system_state() -> dict[str, Any]:
    from cores.health.engine import HealthCenter

    center = HealthCenter()
    summary = center.summary()
    return {
        "status": summary.get("status", "unknown"),
        "score": summary.get("score", 0),
        "running": True,
        "snapshots": len(summary.get("categories", {})),
    }


def _work_bank_status() -> dict[str, Any]:
    bank = get_workbank()
    items = list(bank._items.values()) if hasattr(bank, "_items") else []

    ready = len([i for i in items if getattr(i, "status", "") == "ready_to_deliver"])
    pending = len([i for i in items if getattr(i, "status", "") == "needs_access"])
    preparing = len([i for i in items if getattr(i, "status", "") == "preparing"])
    delivered = len([i for i in items if getattr(i, "status", "") == "delivered"])

    return {
        "ready_to_deliver": ready,
        "needs_access": pending,
        "preparing": preparing,
        "delivered_this_month": delivered,
        "total_active": len(items),
        "monthly_target": 10,
        "monthly_achieved": len([i for i in items if getattr(i, "status", "") == "delivered"]),
    }


def _top_opportunity() -> dict[str, Any] | None:
    """Get the single highest HTROI opportunity for today."""
    bank = get_workbank()
    items = list(bank._items.values()) if hasattr(bank, "_items") else []

    if not items:
        return None

    # Filter ready-to-deliver items
    ready_items = [i for i in items if getattr(i, "status", "") == "ready_to_deliver"]

    if not ready_items:
        return None

    # Rank by EV/human-hour (HTROI)
    ranked = sorted(ready_items, key=lambda i: getattr(i, "htroi_usd_per_hour", 0) or 0, reverse=True)

    top = ranked[0]

    return {
        "id": getattr(top, "id", ""),
        "title": getattr(top, "title", ""),
        "platform": getattr(top, "platform", ""),
        "reward_usd": getattr(top, "reward", 0.0),
        "human_hours": getattr(top, "estimated_time_hours", 1.0) or 1.0,
        "htroi_usd_per_hour": getattr(top, "htroi_usd_per_hour", 0.0),
        "acceptance_probability": getattr(top, "acceptance_probability", 0.0),
        "platform_url": getattr(top, "url", ""),
    }


def _skill_gap_for_top(top_opp: dict[str, Any] | None) -> dict[str, Any] | None:
    if not top_opp:
        return None

    from cores.direct_work_engine.models import EmploymentType, ExperienceLevel, Opportunity, UserProfile
    from cores.direct_work_engine.skill_gap import SkillAmplifier

    # Create user profile for Argentina
    profile = UserProfile(
        name="Adriel",
        country="Argentina",
        languages={"es", "en"},
        skills={"python", "rust", "solidity", "typescript", "go"},
        experience_level=ExperienceLevel.NONE,
        remote_only=True,
        accepts_ai_tools=True,
        availability_hours=40.0,
        has_portfolio=False,
        preferred_payment_methods=[],
        preferred_currencies=["USD"],
        preferred_employment_types=[EmploymentType.BOUNTY, EmploymentType.MICROTASK],
        preferred_categories=[OpportunityCategory.DEV_BOUNTY, OpportunityCategory.AI_EVALUATION],
        min_payment=10.0,
    )

    # Create opportunity object
    opp_id = top_opp.get("id", "")
    opp_title = top_opp.get("title", "")
    opp_platform = top_opp.get("platform", "")
    opp_reward = float(top_opp.get("reward_usd", 0.0))
    opp_hours = top_opp.get("human_hours", 1.0)

    from cores.direct_work_engine.models import EmploymentType, ExperienceLevel

    opp = Opportunity(
        id=opp_id,
        title=opp_title,
        platform=opp_platform,
        category="DEV_BOUNTY",
        reward=opp_reward,
        currency="USD",
        estimated_time_hours=opp_hours,
        difficulty="INTERMEDIATE",
        experience_required=ExperienceLevel.NONE,
        employment_type=EmploymentType.BOUNTY,
        entry_mechanism="ASSESSMENT",
    )

    amplifier = SkillAmplifier()
    report = amplifier.analyze(opp, profile)

    return {
        "missing_skills": report.missing_skills,
        "learning_plan": report.learning_plan,
        "hours_to_ready": sum(s.get("hours", 0) for s in report.learning_plan),
    }


def _recommended_focus() -> dict[str, Any]:
    """HTROI-driven focus recommendation."""
    engine = get_economic_engine_v2()
    engine.get_snapshot()

    best_work = None
    best_htroi = 0.0
    for item in engine.lines.values():
        if item.stream.value == "work" and item.htroi_usd_per_hour and item.htroi_usd_per_hour > best_htroi:
            best_htroi = item.htroi_usd_per_hour
            best_work = item

    actions = []

    if best_work:
        actions.append(
            {
                "action": f"Complete {best_work.title}",
                "platform": best_work.platform,
                "expected_htroi": best_work.htroi_usd_per_hour,
                "human_hours": float(best_work.human_hours_invested),
                "expected_net": float(best_work.net_usd),
                "reason": f"Highest HTROI at ${best_htroi}/hr human time",
            }
        )

    # Check work bank for ready items
    from cores.direct_work_engine.workbank import get_workbank

    bank = get_workbank()
    ready_items = (
        [i for i in bank._items.values() if getattr(i, "status", "") == "ready_to_deliver"]
        if hasattr(bank, "_items")
        else []
    )

    for item in ready_items[:3]:
        actions.append(
            {
                "action": f"Deliver {item.title}",
                "platform": item.platform,
                "reward_usd": item.reward,
                "reason": "Ready to deliver — just needs your approval",
            }
        )

    if not actions:
        return {"primary": "No high-HTROI work available today", "details": []}

    return {
        "primary": actions[0]["action"],
        "details": actions,
        "htroi_leader": actions[0].get("expected_htroi", 0) if actions else 0,
    }


def _ai_activity_summary() -> dict[str, Any]:
    """Summarize AI agent activity from the last 24h."""
    return {
        "completed": 0,
        "failed": 0,
        "pending": 0,
        "time_saved_hours": 0,
        "auto_repairs": 0,
    }


def _revenue_snapshot() -> dict[str, Any]:
    engine = get_economic_engine_v2()
    snapshot = engine.get_snapshot()
    return {
        "work": {
            "expected": float(snapshot.work_expected),
            "committed": float(snapshot.work_committed),
            "realized": float(snapshot.work_realized),
            "paid": float(snapshot.work_paid),
            "net": float(snapshot.work_net),
        },
        "trading": {
            "expected": float(snapshot.trading_expected),
            "realized": float(snapshot.trading_realized),
            "paid": float(snapshot.trading_paid),
            "net": float(snapshot.trading_net),
        },
        "capital": {
            "expected": float(snapshot.capital_expected),
            "realized": float(snapshot.capital_realized),
            "net": float(snapshot.capital_net),
        },
        "total": {
            "expected": float(snapshot.total_expected),
            "realized": float(snapshot.total_realized),
            "paid": float(snapshot.total_paid),
            "net": float(snapshot.total_net),
        },
        "costs": {
            "fees": float(snapshot.total_fees_usd),
            "tax": float(snapshot.total_tax_usd),
            "fx_loss": float(snapshot.total_fx_loss_usd),
        },
    }


def _compute_htroi_for_opportunity(opp: dict[str, Any]) -> dict[str, Any] | None:
    """Compute HTROI for a single opportunity."""
    try:
        htroi = compute_htroi(
            expected_income_usd=opp.get("reward_usd", 0.0),
            human_hours=opp.get("human_hours", 1.0),
            confidence=opp.get("acceptance_probability", 0.5),
        )
        return {
            "roi_usd_per_hour": htroi.roi_usd_per_hour,
            "expected_income_usd": htroi.expected_income_usd,
            "human_hours_total": htroi.human_hours_total,
            "confidence_applied": htroi.confidence_applied,
            "compression_pct": htroi.compression_pct,
        }
    except Exception as e:
        logger.warning("HTROI computation failed: %s", e)
        return None


def _greeting() -> str:
    hour = datetime.now(UTC).hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def _projection(
    work_income_usd_per_month: float,
    savings_usd_per_month: float,
    start_capital_usd: float,
    annual_return_rate: float,
    target_monthly_usd: float,
) -> dict[str, Any]:
    from cores.direct_work_engine.income_projection import project_income

    if work_income_usd_per_month <= 0 and savings_usd_per_month <= 0:
        return {"crossing_months": None, "months_to_target": None, "note": "Configure income/savings for projections"}

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


def daily_brief_v2_api(
    work_income_usd_per_month: float = 0.0,
    savings_usd_per_month: float = 0.0,
    start_capital_usd: float = 0.0,
    annual_return_rate: float = 0.10,
    target_monthly_usd: float = 100_000.0,
) -> dict[str, Any]:
    """API endpoint wrapper for Daily Brief V2."""
    return daily_brief_v2(
        work_income_usd_per_month=work_income_usd_per_month,
        savings_usd_per_month=savings_usd_per_month,
        start_capital_usd=start_capital_usd,
        annual_return_rate=annual_return_rate,
        target_monthly_usd=target_monthly_usd,
    )


__all__ = ["daily_brief_v2", "daily_brief_v2_api"]
