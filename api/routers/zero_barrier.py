"""Zero-Barrier Income Opportunities API Router.

Provides endpoints for zero-barrier income opportunities (no interview, portfolio, experience required).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.revenue_tracker.RevenueTracker import (
    BarrierType,
    PaymentPlatform,
    PaymentStatus,
    RevenueTracker,
    get_revenue_tracker,
)

logger = logging.getLogger("ownex.api.zero_barrier")


router = APIRouter(prefix="/zero-barrier", tags=["zero-barrier"])


class ZeroBarrierOpportunityRequest(BaseModel):
    """Request to create a zero-barrier opportunity."""

    id: str
    platform: str
    title: str
    description: str
    amount: float
    currency: str = "USD"
    difficulty: str = "beginner"
    success_rate: float = 0.0
    time_estimate: str = ""
    tags: list[str] = []
    skills_required: list[str] = []
    url: str = ""
    barriers: list[str] = ["none"]  # Default to zero-barrier


class ZeroBarrierOpportunityResponse(BaseModel):
    """Response for zero-barrier opportunity."""

    id: str
    platform: str
    title: str
    description: str
    amount: float
    currency: str
    difficulty: str
    success_rate: float
    time_estimate: str
    tags: list[str]
    skills_required: list[str]
    url: str
    is_zero_barrier: bool
    potential_earnings: float


@router.get("/opportunities", response_model=list[ZeroBarrierOpportunityResponse])
async def get_zero_barrier_opportunities(
    platform: str | None = None,
    min_amount: float = 0.0,
    difficulty: str | None = None,
) -> list[ZeroBarrierOpportunityResponse]:
    """Get zero-barrier opportunities (no interview, portfolio, experience required)."""
    tracker = get_revenue_tracker()

    try:
        opportunities = tracker.get_zero_barrier_opportunities(
            platform=platform,
            min_amount=Decimal(str(min_amount)),
            difficulty=difficulty,
        )

        responses = []
        for op in opportunities:
            responses.append(
                ZeroBarrierOpportunityResponse(
                    id=op.id,
                    platform=op.platform,
                    title=op.title,
                    description=op.description,
                    amount=float(op.amount),
                    currency=op.currency,
                    difficulty=op.difficulty,
                    success_rate=op.success_rate,
                    time_estimate=op.time_estimate,
                    tags=op.tags,
                    skills_required=op.skills_required,
                    url=op.url,
                    is_zero_barrier=op.is_zero_barrier(),
                    potential_earnings=float(op.get_potential_earnings()),
                )
            )

        return responses

    except Exception as e:
        logger.error(f"[ZERO-BARRIER] Error getting opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/opportunities")
async def create_zero_barrier_opportunity(request: ZeroBarrierOpportunityRequest) -> dict[str, Any]:
    """Create a zero-barrier opportunity."""
    tracker = get_revenue_tracker()

    try:
        from cores.revenue_tracker.RevenueTracker import RevenueOpportunity

        # Convert barrier strings to BarrierType enums
        barrier_types = []
        for barrier_str in request.barriers:
            try:
                barrier_types.append(BarrierType(barrier_str))
            except ValueError:
                barrier_types.append(BarrierType.NONE)

        opportunity = RevenueOpportunity(
            id=request.id,
            platform=request.platform,
            title=request.title,
            description=request.description,
            amount=Decimal(str(request.amount)),
            currency=request.currency,
            status=PaymentStatus.PENDING,
            barriers=barrier_types,
            difficulty=request.difficulty,
            success_rate=request.success_rate,
            time_estimate=request.time_estimate,
            tags=request.tags,
            skills_required=request.skills_required,
            url=request.url,
        )

        tracker.create_opportunity(opportunity)

        return {
            "success": True,
            "message": "Zero-barrier opportunity created successfully",
            "opportunity_id": opportunity.id,
        }

    except Exception as e:
        logger.error(f"[ZERO-BARRIER] Error creating opportunity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_zero_barrier_stats() -> dict[str, Any]:
    """Get zero-barrier opportunity statistics."""
    tracker = get_revenue_tracker()

    try:
        opportunities = tracker.get_zero_barrier_opportunities()

        total_opportunities = len(opportunities)
        total_potential_earnings = sum(op.get_potential_earnings() for op in opportunities)
        total_amount = sum(op.amount for op in opportunities)

        by_platform: dict[str, dict[str, Any]] = {}
        for op in opportunities:
            if op.platform not in by_platform:
                by_platform[op.platform] = {
                    "count": 0,
                    "total_amount": Decimal("0"),
                    "potential_earnings": Decimal("0"),
                }
            by_platform[op.platform]["count"] += 1
            by_platform[op.platform]["total_amount"] += op.amount
            by_platform[op.platform]["potential_earnings"] += op.get_potential_earnings()

        return {
            "total_opportunities": total_opportunities,
            "total_amount": float(total_amount),
            "total_potential_earnings": float(total_potential_earnings),
            "by_platform": {
                platform: {
                    "count": data["count"],
                    "total_amount": float(data["total_amount"]),
                    "potential_earnings": float(data["potential_earnings"]),
                }
                for platform, data in by_platform.items()
            },
        }

    except Exception as e:
        logger.error(f"[ZERO-BARRIER] Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platforms")
async def get_zero_barrier_platforms() -> dict[str, Any]:
    """Get available zero-barrier platforms."""
    platforms = {
        "bug_bounty": {
            "name": "Bug Bounty",
            "platforms": ["HackerOne", "Bugcrowd", "Intigriti", "YesWeHack", "Synack"],
            "description": "Find vulnerabilities in software and get paid",
            "avg_reward": 500.0,
            "success_rate": 0.15,
        },
        "open_source_bounty": {
            "name": "Open Source Bounties",
            "platforms": ["Gitcoin", "GitHub Sponsors", "Bountysource", "IssueHunt"],
            "description": "Complete open source tasks and get paid",
            "avg_reward": 150.0,
            "success_rate": 0.40,
        },
        "micro_task": {
            "name": "Micro Tasks",
            "platforms": ["Amazon Mechanical Turk", "Clickworker", "Microworkers", "Figure Eight"],
            "description": "Complete small tasks for pay",
            "avg_reward": 5.0,
            "success_rate": 0.85,
        },
        "affiliate": {
            "name": "Affiliate Marketing",
            "platforms": ["Amazon Associates", "ShareASale", "ClickBank", "Rakuten"],
            "description": "Promote products and earn commissions",
            "avg_reward": 25.0,
            "success_rate": 0.20,
        },
        "gamification": {
            "name": "Gamification",
            "platforms": ["Swagbucks", "InboxDollars", "Survey Junkie", "UserTesting"],
            "description": "Complete gamified tasks for rewards",
            "avg_reward": 10.0,
            "success_rate": 0.90,
        },
    }

    return {"platforms": platforms}
