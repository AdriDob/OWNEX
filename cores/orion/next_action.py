"""Next Action Engine — scores all possible actions and returns the ONE best.

Prioritizes beginner-friendly, high-EVH, low-effort opportunities.
Always returns a single recommended action with explanation.
"""

from __future__ import annotations

import logging
from typing import Any

from cores.opportunity import get_engine as get_opp_engine
from cores.opportunity.models import Opportunity

logger = logging.getLogger("catseye.cateye.next_action")


def _score_action(opp: Opportunity) -> float:
    """Score an opportunity as a candidate next action.

    Higher is better. Factors:
    - EVH (expected value per hour) — primary
    - Execution score (lower effort = better)
    - Competition score (less competition = better)
    - Confidence score
    """
    score = opp.score
    if not score:
        return 0.0

    evh = score.evh.value if score.evh and score.evh.value else 0.0
    exec_s = getattr(score, "execution_score", 0.5)
    comp_s = getattr(score, "competition_score", 0.5)
    conf_s = getattr(score, "confidence_score", 0.5)

    # Normalize evh to 0-1 range (cap at 200)
    evh_norm = min(evh / 200.0, 1.0)

    # Weighted combination favoring low effort + high value
    return (
        evh_norm * 0.4 +
        (1.0 - exec_s) * 0.25 +  # invert: lower execution score = easier = better
        comp_s * 0.2 +
        conf_s * 0.15
    )


def _estimate_reward(opp: Opportunity) -> str:
    """Return a human-readable reward estimate."""
    score = opp.score
    if not score:
        return "Unknown"
    max_r = score.reward_potential
    min_r = 0
    if max_r and min_r:
        return f"${min_r}-${max_r}"
    if max_r:
        return f"Up to ${max_r}"
    return "Unknown"


def _estimate_effort(opp: Opportunity) -> str:
    """Return a human-readable effort estimate."""
    score = opp.score
    if not score:
        return "medium"
    exec_s = getattr(score, "execution_score", 0.5)
    if exec_s > 0.7:
        return "low"
    if exec_s > 0.4:
        return "medium"
    return "high"


def _generate_steps(opp: Opportunity) -> list[str]:
    """Generate step-by-step guidance for this opportunity."""
    cat = opp.category if opp.category else ""
    base = [
        f"Review opportunity: {opp.name}",
        "Understand the scope and target",
    ]
    if cat in ("web", "api"):
        base.extend([
            "Run a basic reconnaissance scan",
            "Document any findings",
        ])
    elif cat in ("web3",):
        base.extend([
            "Review smart contract if available",
            "Check for common web3 vulnerabilities",
        ])
    else:
        base.extend([
            "Analyze the target surface",
            "Identify potential entry points",
        ])
    base.append("Generate a structured report of your findings")
    return base


def get_next_action() -> dict[str, Any] | None:
    """Return the single best next action, or None if none available."""
    logger.info("[CATEYE] get_next_action called")
    try:
        engine = get_opp_engine()
        all_opps = engine.get_all()
    except Exception:
        logger.warning("[CATEYE] failed to get opportunities", exc_info=True)
        return None

    if not all_opps:
        logger.info("[CATEYE] no opportunities available")
        return None

    # Score and rank
    ranked = [(opp, _score_action(opp)) for opp in all_opps]
    ranked.sort(key=lambda x: x[1], reverse=True)

    best_opp, best_score = ranked[0]
    logger.info("[CATEYE] best action: %s (score=%.4f)", best_opp.name, best_score)

    if best_score <= 0:
        return None

    return {
        "id": best_opp.id,
        "title": f"Analyze: {best_opp.name}",
        "type": "analyze_opportunity",
        "effort": _estimate_effort(best_opp),
        "estimated_reward": _estimate_reward(best_opp),
        "why_now": _pick_why_now(best_opp),
        "steps": _generate_steps(best_opp),
    }


def _pick_why_now(opp: Opportunity) -> str:
    """Return a one-sentence explanation of why this action is recommended now."""
    score = opp.score
    if not score:
        return "This is your top-ranked opportunity"
    if score.evh and score.evh.value and score.evh.value > 50:
        return "Highest value-per-hour opportunity — efficient use of your time"
    if getattr(score, "competition_score", 0) > 0.7:
        return "Low competition means higher chance of success"
    if getattr(score, "reward_score", 0) > 0.7:
        return "Highest reward potential among your opportunities"
    return "Best overall opportunity based on effort vs reward"
