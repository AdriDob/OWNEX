"""Adapter — convert CATEYE opportunities (cores) to OWNEX format (core)."""

from __future__ import annotations

from datetime import UTC, datetime

from core.opportunity.models import PersonalHistory, ScoredOpportunity
from core.opportunity.scorer import score_opportunity
from cores.opportunity.models import Opportunity


def _map_category_to_cycle(category: str) -> str:
    """Map old opportunity category to OWNEX work cycle."""
    mapping = {
        "platform": "security",
        "independent": "forge",
        "web3": "forge",
        "emerging": "atlas",
        "research": "atlas",
        "ai": "pulse",
        "infrastructure": "security",
        "cloud": "security",
        "mobile": "security",
        "browser_extension": "security",
        "api_ecosystem": "security",
        "open_source": "forge",
        "paid_research": "vault",
    }
    return mapping.get(category, "security")


def _map_category_to_source_type(category: str) -> str:
    """Map category to OWNEX source_type."""
    mapping = {
        "platform": "platform",
        "independent": "independent",
        "web3": "web3",
        "emerging": "emerging",
        "research": "research",
        "ai": "ai",
        "infrastructure": "infrastructure",
        "cloud": "cloud",
        "mobile": "mobile",
        "browser_extension": "browser_extension",
        "api_ecosystem": "api",
        "open_source": "open_source",
        "paid_research": "paid_research",
    }
    return mapping.get(category, "platform")


def _estimate_effort_hours(opp: Opportunity) -> float:
    """Estimate effort hours from old opportunity."""
    base = opp.estimated_effort_hours or 1.0
    if opp.category == "web3":
        return max(base, 4.0)
    if opp.category in ("emerging", "research"):
        return max(base, 8.0)
    return base


def adapt_opportunity(
    opp: Opportunity,
    personal: PersonalHistory | None = None,
) -> ScoredOpportunity:
    """
    Convert a CATEYE Opportunity to OWNEX ScoredOpportunity.
    Uses OWNEX scoring engine with personal history for personalized ranking.
    """
    cycle = _map_category_to_cycle(opp.category)
    source_type = _map_category_to_source_type(opp.category)
    source_name = opp.source.name if opp.source else "unknown"
    platform = opp.source.name if opp.source else opp.category

    return score_opportunity(
        opp_id=opp.id,
        name=opp.name,
        cycle=cycle,
        source_type=source_type,
        source_name=source_name,
        reward=opp.estimated_payout or 0.0,
        effort_hours=_estimate_effort_hours(opp),
        platform=platform,
        technology_tags=list(opp.technology_tags),
        url=opp.public_url,
        created_at=opp.created_at or datetime.now(UTC).isoformat(),
        personal=personal,
        original=opp,
    )


def adapt_opportunities(
    opportunities: list[Opportunity],
    personal: PersonalHistory | None = None,
) -> list[ScoredOpportunity]:
    """Batch convert list of opportunities."""
    return [adapt_opportunity(opp, personal) for opp in opportunities]
