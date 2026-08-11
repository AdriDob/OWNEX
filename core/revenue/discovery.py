from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.opportunity.models import ScoredOpportunity


def discover_daily_opportunities(
    scored: list[ScoredOpportunity],
    top_n: int = 10,
) -> list[dict[str, Any]]:
    """Discover and rank daily opportunities from scored opportunities.

    Takes the output of the scoring engine and returns a daily
    discovery feed with the best matches for today.
    """
    if not scored:
        return []

    sorted_opps = sorted(scored, key=lambda o: o.score.overall, reverse=True)

    today = datetime.now(UTC).strftime("%Y-%m-%d")

    discovered: list[dict[str, Any]] = []
    for opp in sorted_opps[:top_n]:
        discovered.append(
            {
                "date": today,
                "id": opp.id,
                "name": opp.name,
                "cycle": opp.cycle,
                "source_type": opp.source_type,
                "platform": opp.platform,
                "reward_usd": opp.reward,
                "effort_hours": opp.effort_hours,
                "score_overall": opp.score.overall,
                "score_ev": opp.score.expected_value,
                "score_acceptance": opp.score.acceptance_probability,
                "url": opp.url,
                "recommended_action": _recommend_action(opp),
            }
        )

    return discovered


def _recommend_action(opp: ScoredOpportunity) -> str:
    if opp.score.overall >= 0.8:
        return "HIGH_PRIORITY"
    if opp.score.overall >= 0.6:
        return "WORTH_PREPARING"
    if opp.score.overall >= 0.4:
        return "LOW_PRIORITY"
    return "SKIP"
