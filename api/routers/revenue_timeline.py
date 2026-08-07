"""Revenue Timeline API router.

Exposes OWNEX revenue progression timeline from zero to target tiers.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.revenue_tracker.revenue_timeline import (
    TIER_TARGETS,
    calculate_revenue_timeline,
    find_target_month,
)

router = APIRouter(prefix="/revenue-timeline", tags=["revenue-timeline"])


class TimelineRequest(BaseModel):
    """Request for revenue timeline calculation."""

    target_tier: str = "conservative"  # conservative, moderate, aggressive, maximum


class TimelineResponse(BaseModel):
    """Response with full revenue timeline."""

    target_tier: str
    target_monthly_revenue: float
    target_achieved_month: int
    timeline: list[dict]
    summary: dict


class MilestoneResponse(BaseModel):
    """Response with key revenue milestones."""

    target_tier: str
    first_1k_month: int
    first_10k_month: int
    first_100k_month: int
    conservative_tier_month: int | None
    total_months_analyzed: int


@router.post("/calculate", response_model=TimelineResponse)
async def calculate_timeline(request: TimelineRequest) -> TimelineResponse:
    """Calculate revenue timeline from zero to target tier.

    Args:
        request: TimelineRequest with target_tier

    Returns:
        TimelineResponse with full progression data
    """

    valid_tiers = ["conservative", "moderate", "aggressive", "maximum"]
    if request.target_tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}")

    timeline = calculate_revenue_timeline(request.target_tier)

    target = TIER_TARGETS.get(request.target_tier, TIER_TARGETS["conservative"])
    target_month = find_target_month(timeline, target)

    # Convert timeline to dict for JSON serialization
    timeline_dicts = []
    for month_data in timeline:
        timeline_dicts.append(
            {
                "month": month_data.month,
                "phase": month_data.phase.value,
                "bug_bounty": month_data.bug_bounty,
                "dev_bounty": month_data.dev_bounty,
                "data_annotation": month_data.data_annotation,
                "trading": month_data.trading,
                "investment": month_data.investment,
                "market_intelligence": month_data.market_intelligence,
                "ccxt_multi_exchange": month_data.ccxt_multi_exchange,
                "forex": month_data.forex,
                "futures": month_data.futures,
                "global_arbitrage": month_data.global_arbitrage,
                "memecoin": month_data.memecoin,
                "polymarket": month_data.polymarket,
                "sports_betting": month_data.sports_betting,
                "total": month_data.total,
                "cumulative": month_data.cumulative,
                "assumptions": month_data.assumptions,
            }
        )

    # Calculate summary
    summary = {
        "total_months": len(timeline),
        "total_cumulative": timeline[-1].cumulative if timeline else 0,
        "average_monthly": sum(m.total for m in timeline) / len(timeline) if timeline else 0,
        "first_1k_month": next((m.month for m in timeline if m.total >= 1000), None),
        "first_10k_month": next((m.month for m in timeline if m.total >= 10000), None),
        "first_100k_month": next((m.month for m in timeline if m.total >= 100000), None),
    }

    return TimelineResponse(
        target_tier=request.target_tier,
        target_monthly_revenue=target,
        target_achieved_month=target_month,
        timeline=timeline_dicts,
        summary=summary,
    )


@router.get("/milestones", response_model=MilestoneResponse)
async def get_milestones(target_tier: str = "conservative") -> MilestoneResponse:
    """Get key revenue milestones for a target tier.

    Args:
        target_tier: Target revenue tier

    Returns:
        MilestoneResponse with key month milestones
    """

    valid_tiers = ["conservative", "moderate", "aggressive", "maximum"]
    if target_tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}")

    timeline = calculate_revenue_timeline(target_tier)

    target = TIER_TARGETS.get(target_tier, TIER_TARGETS["conservative"])
    target_month = find_target_month(timeline, target)

    return MilestoneResponse(
        target_tier=target_tier,
        first_1k_month=next((m.month for m in timeline if m.total >= 1000), None),
        first_10k_month=next((m.month for m in timeline if m.total >= 10000), None),
        first_100k_month=next((m.month for m in timeline if m.total >= 100000), None),
        conservative_tier_month=target_month if target_tier == "conservative" else None,
        total_months_analyzed=len(timeline),
    )


@router.get("/compare")
async def compare_tiers() -> dict:
    """Compare all revenue tiers side by side.

    Returns:
        Dict with comparison data for all tiers
    """

    tiers = ["conservative", "moderate", "aggressive", "maximum"]
    comparison = {}

    for tier in tiers:
        timeline = calculate_revenue_timeline(tier)
        target = TIER_TARGETS[tier]
        target_month = find_target_month(timeline, target)

        comparison[tier] = {
            "target_monthly_revenue": target,
            "target_achieved_month": target_month,
            "first_1k_month": next((m.month for m in timeline if m.total >= 1000), None),
            "first_10k_month": next((m.month for m in timeline if m.total >= 10000), None),
            "first_100k_month": next((m.month for m in timeline if m.total >= 100000), None),
            "total_cumulative_24mo": timeline[-1].cumulative if timeline else 0,
        }

    return comparison
