"""Daily Brief API — Answers the question: "What should I do now?"

Generates a ranked list of actions with:
- Expected value (USD)
- Time estimate
- Probability of success
- Next concrete action (button)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger("ownex.api.daily_brief")

router = APIRouter(prefix="/api/daily-brief", tags=["daily-brief"])


def _get_recommender() -> Any:  # type: ignore[no-untyped-def]
    """Get the Direct Work Engine recommender."""
    try:
        from cores.direct_work_engine import get_direct_work_engine

        dwe = get_direct_work_engine()
        return dwe.recommender
    except Exception:
        return None


def _get_workbank() -> Any:  # type: ignore[no-untyped-def]
    """Get the WorkBank."""
    try:
        from cores.direct_work_engine.workbank import get_workbank

        return get_workbank()
    except Exception:
        return None


def _get_revenue_tracker() -> Any:  # type: ignore[no-untyped-def]
    """Get the RevenueTracker."""
    try:
        from cores.revenue_tracker.tracker import get_revenue_tracker

        return get_revenue_tracker()
    except Exception:
        return None


@router.get("")
async def daily_brief() -> dict[str, Any]:
    """Generate the Daily Brief — ranked actions for today.

    Returns:
    - actions: List of ranked actions with EV, time, probability, next step
    - summary: Quick stats (total EV, pending work, revenue today)
    - blocked: Items waiting for human approval
    - completed_today: Items completed today
    """
    actions: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    completed_today: list[dict[str, Any]] = []

    # 1. Get recommendations from Direct Work Engine
    try:
        from cores.direct_work_engine.models import UserProfile

        recommender = _get_recommender()
        if recommender:
            profile = UserProfile(name="OWNEX User")
            # Get top opportunities ranked by EV
            engine = None
            try:
                from cores.direct_work_engine import get_direct_work_engine

                engine = get_direct_work_engine()
                opps = await engine.discovery.discover_all() if engine else []
            except Exception:
                opps = []

            if opps:
                ranked = recommender.recommend(opps, profile, limit=10) or []
                for r in ranked[:10]:
                    opp = r.opportunity if hasattr(r, "opportunity") else r
                    score = getattr(r, "final_score", getattr(r, "score", 0))
                    ev_hr = getattr(opp, "expected_value_usd_per_hour", 0)
                    prob = getattr(opp, "acceptance_probability", 0.5)
                    reward = getattr(opp, "payment", getattr(opp, "estimated_reward_usd", 0))
                    hours = getattr(opp, "estimated_time_hours", 2.0)

                    actions.append(
                        {
                            "id": getattr(opp, "id", "unknown"),
                            "title": getattr(opp, "title", "Untitled"),
                            "platform": getattr(opp, "platform", "unknown"),
                            "category": getattr(opp, "category", "unknown"),
                            "expected_value_usd": round(reward * prob, 2),
                            "expected_value_per_hour": round(ev_hr, 2),
                            "probability": round(prob, 2),
                            "estimated_hours": round(hours, 1),
                            "reward_usd": round(reward, 2),
                            "score": round(score, 3),
                            "url": getattr(opp, "url", ""),
                            "next_action": _determine_next_action(opp),
                            "action_type": "opportunity",
                        }
                    )
    except Exception as exc:
        logger.debug("Daily brief opportunity scan failed: %s", exc)

    # 2. Get work bank items ready for delivery
    try:
        bank = _get_workbank()
        if bank:
            items = bank.get_items_by_status("ready") if hasattr(bank, "get_items_by_status") else []
            for item in (items or [])[:5]:
                actions.append(
                    {
                        "id": getattr(item, "id", "unknown"),
                        "title": f"Deliver: {getattr(item, 'title', 'Untitled')}",
                        "platform": getattr(item, "platform", "unknown"),
                        "category": "delivery",
                        "expected_value_usd": getattr(item, "estimated_reward_usd", 0),
                        "probability": 0.9,
                        "next_action": "Submit delivery",
                        "action_type": "delivery",
                    }
                )
    except Exception as exc:
        logger.debug("Daily brief workbank scan failed: %s", exc)

    # 3. Get pending approvals (from WorkerCore)
    try:
        from cores.worker_core import get_worker_core

        worker = get_worker_core()
        for wid, witem in worker.work_items.items():
            if witem.human_action_required:
                blocked.append(
                    {
                        "id": wid,
                        "title": witem.title,
                        "phase": witem.phase.value,
                        "description": witem.human_action_description or "Approval needed",
                        "platform": witem.platform,
                    }
                )
            elif witem.state.value == "running":
                completed_today.append(
                    {
                        "id": wid,
                        "title": witem.title,
                        "phase": witem.phase.value,
                    }
                )
    except Exception:
        pass

    # 4. Sort actions by expected value
    actions.sort(key=lambda a: a.get("expected_value_usd", 0), reverse=True)

    # 5. Build summary
    total_ev = sum(a.get("expected_value_usd", 0) for a in actions)
    today_revenue = 0.0
    try:
        tracker = _get_revenue_tracker()
        if tracker and hasattr(tracker, "get_today_summary"):
            today_revenue = tracker.get_today_summary().get("total_usd", 0)
    except Exception:
        pass

    return {
        "actions": actions,
        "blocked": blocked,
        "completed_today": completed_today,
        "summary": {
            "total_expected_usd": round(total_ev, 2),
            "action_count": len(actions),
            "blocked_count": len(blocked),
            "completed_count": len(completed_today),
            "revenue_today_usd": round(today_revenue, 2),
        },
        "greeting": _greeting(),
    }


def _determine_next_action(opp: Any) -> str:
    """Determine the next concrete action for an opportunity."""
    platform = getattr(opp, "platform", "").lower()
    category = getattr(opp, "category", "").lower()

    if "bug_bounty" in category or "security" in category:
        return "Start reconnaissance"
    elif "software_engineering" in category or "backend" in category or "frontend" in category:
        return "Analyze issue and generate fix"
    elif platform in ("outlier", "mindrift", "dataannotation"):
        return "Open platform and start task"
    elif platform in ("fiverr", "upwork"):
        return "Review requirements and prepare proposal"
    elif "ai_training" in category or "ai_evaluation" in category:
        return "Open platform and begin evaluation"
    else:
        return "Review opportunity details"


def _greeting() -> str:
    """Generate a time-appropriate greeting."""
    from datetime import UTC, datetime

    hour = datetime.now(UTC).hour
    if hour < 6:
        return "Night owl mode — focus on high-EV opportunities"
    elif hour < 12:
        return "Good morning — let's find today's best opportunity"
    elif hour < 18:
        return "Good afternoon — time to execute and deliver"
    else:
        return "Evening wrap-up — review completed work and plan tomorrow"
