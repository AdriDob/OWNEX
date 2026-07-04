"""CATEYE Context Engine — aggregates system state into a unified decision context.

Combines opportunities, assistant insights, pipeline state, and daily briefing
into a single response that answers "What should I do next?"
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from cores.opportunity import get_engine as get_opp_engine
from cores.opportunity.models import Opportunity, OpportunityRecommendations

logger = logging.getLogger("catseye.cateye.context")


def _opp_to_preview(opp: Opportunity) -> dict[str, Any]:
    """Convert an Opportunity to a lightweight preview dict."""
    score = opp.score
    return {
        "id": opp.id,
        "title": opp.name,
        "source": opp.source.name if opp.source else "unknown",
        "url": opp.source.url if opp.source else "",
        "category": opp.category if opp.category else "general",
        "priority": opp.priority or "medium",
        "reward": f"${score.reward_potential}" if score and score.reward_potential else "Unknown",
        "effort": _effort_label(opp),
        "reason": _pick_reason(opp),
        "evh": round(score.evh.value, 2) if score and score.evh else None,
    }


def _effort_label(opp: Opportunity) -> str:
    """Estimate effort from score fields."""
    if not opp.score:
        return "medium"
    score = opp.score
    exec_score = score.execution_score if hasattr(score, "execution_score") else 0.5
    if exec_score > 0.7:
        return "low"
    if exec_score > 0.4:
        return "medium"
    return "high"


def _pick_reason(opp: Opportunity) -> str:
    """Pick a human-readable reason this opportunity matters."""
    score = opp.score
    if not score:
        return "Review this opportunity"
    if score.evh and score.evh.value and score.evh.value > 50:
        return "High value per hour — efficient use of time"
    if score.competition_estimate and score.competition_estimate > 0.7:
        return "Low competition — higher chance of success"
    reward_val = score.breakdown.reward_score if score.breakdown else score.reward_potential
    if reward_val and reward_val > 0.7:
        return "High reward potential"
    return "Promising opportunity worth reviewing"


def _get_progress() -> dict[str, Any]:
    """Compute user progress metrics from existing system data."""
    try:
        engine = get_opp_engine()
        all_opps = engine.get_all()
        scored = [o for o in all_opps if o.score is not None]
        return {
            "opportunities_available": len(all_opps),
            "opportunities_scored": len(scored),
            "next_milestone": "Review your top 3 opportunities this week",
        }
    except Exception:
        return {
            "opportunities_available": 0,
            "opportunities_scored": 0,
            "next_milestone": "System initializing...",
        }


def _get_guided_paths() -> list[dict[str, Any]]:
    """Return beginner-friendly guided paths."""
    return [
        {
            "id": "beginner_web",
            "name": "Beginner Web Vulnerability Checks",
            "description": "Learn to identify common web vulnerabilities step by step",
            "progress": "0/5 steps",
            "effort": "2-3 hours",
        },
        {
            "id": "auto_review",
            "name": "Automated Opportunity Review",
            "description": "Let the system find and rank the best opportunities for you",
            "progress": "0/3 steps",
            "effort": "30 minutes",
        },
        {
            "id": "report_gen",
            "name": "Report Generation Tasks",
            "description": "Generate structured reports from your findings",
            "progress": "0/4 steps",
            "effort": "1-2 hours",
        },
    ]


def _build_summary(
    next_action: dict[str, Any] | None,
    opportunities: list[dict[str, Any]],
    progress: dict[str, Any],
) -> str:
    """Build a human-readable one-paragraph summary."""
    parts = []
    opp_count = progress.get("opportunities_available", 0)
    if opp_count == 0:
        return "System initializing. No opportunities discovered yet. Run a scan or import targets to get started."

    if next_action:
        title = next_action.get("title", "review opportunities")
        reward = next_action.get("estimated_reward", "Unknown")
        effort = next_action.get("effort", "medium")
        parts.append(
            f"You have {opp_count} opportunities ready. "
            f"Your top recommended action is to '{title}' — "
            f"estimated effort: {effort}, potential reward: {reward}."
        )
    else:
        parts.append(f"You have {opp_count} opportunities ready to review.")

    if opportunities:
        top = opportunities[0]
        parts.append(f"Start with '{top['title']}' — {top.get('reason', '')}")

    return " ".join(parts)


def get_context() -> dict[str, Any]:
    """Return the unified CATEYE context for the frontend."""
    logger.info("[CATEYE] get_context called")

    from cores.orion.next_action import get_next_action

    next_action = get_next_action()
    progress = _get_progress()

    engine = get_opp_engine()
    recommendations: OpportunityRecommendations | None = None
    try:
        recommendations = engine.get_recommendations()
    except Exception:
        logger.warning("[CATEYE] failed to get recommendations", exc_info=True)

    opportunities: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # Collect from recommendations first (ranked)
    if recommendations:
        for rec_list in [
            recommendations.fast_roi or [],
            recommendations.top_opportunities or [],
            recommendations.low_competition or [],
        ]:
            for opp in rec_list:
                if opp.id not in seen_ids:
                    seen_ids.add(opp.id)
                    opportunities.append(_opp_to_preview(opp))
                    if len(opportunities) >= 5:
                        break
            if len(opportunities) >= 5:
                break

    # Fallback: collect from all opportunities
    if len(opportunities) < 5:
        try:
            all_opps = engine.get_all()
            for opp in all_opps:
                if opp.id not in seen_ids:
                    seen_ids.add(opp.id)
                    opportunities.append(_opp_to_preview(opp))
                    if len(opportunities) >= 5:
                        break
        except Exception:
            logger.warning("[CATEYE] failed to list all opportunities", exc_info=True)

    summary = _build_summary(next_action, opportunities, progress)

    return {
        "summary": summary,
        "next_action": next_action,
        "opportunities": opportunities[:5],
        "progress": progress,
        "guided_paths": _get_guided_paths(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
