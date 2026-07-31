"""Zero-Barrier Income Opportunities API Router.

Provides endpoints for zero-barrier income opportunities (no interview, portfolio, experience required).
Focused on: Bug Bounty, Dev Bounty, Data Annotation.
Integrates with existing platform connectors (cores/platforms/).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.revenue_tracker.revenue_potential import generate_revenue_report
from cores.revenue_tracker.RevenueTracker import (
    BarrierType,
    PaymentStatus,
    get_revenue_tracker,
)

logger = logging.getLogger("ownex.api.zero_barrier")


router = APIRouter(prefix="/zero-barrier", tags=["zero-barrier"])


class ZeroBarrierOpportunityRequest(BaseModel):
    """Request to create a zero-barrier opportunity."""

    id: str
    platform: str  # bug_bounty, dev_bounty, data_annotation
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
    platform: str | None = None,  # bug_bounty, dev_bounty, data_annotation
    min_amount: float = 0.0,
    difficulty: str | None = None,
) -> list[ZeroBarrierOpportunityResponse]:
    """Get zero-barrier opportunities (no interview, portfolio, experience required).

    Platforms:
    - bug_bounty: HackerOne, Bugcrowd, Intigriti, YesWeHack, Synack
    - dev_bounty: Gitcoin, GitHub Sponsors, Bountysource
    - data_annotation: Labelbox, Scale AI, Amazon Mechanical Turk
    """
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
    """Create a zero-barrier opportunity.

    Platforms:
    - bug_bounty: HackerOne, Bugcrowd, Intigriti, YesWeHack, Synack
    - dev_bounty: Gitcoin, GitHub Sponsors, Bountysource
    - data_annotation: Labelbox, Scale AI, Amazon Mechanical Turk
    """
    tracker = get_revenue_tracker()

    # Validate platform
    valid_platforms = ["bug_bounty", "dev_bounty", "data_annotation"]
    if request.platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}",
        )

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
    """Get zero-barrier opportunity statistics.

    Platforms:
    - bug_bounty: HackerOne, Bugcrowd, Intigriti, YesWeHack, Synack
    - dev_bounty: Gitcoin, GitHub Sponsors, Bountysource
    - data_annotation: Labelbox, Scale AI, Amazon Mechanical Turk
    """
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
    """Get available zero-barrier platforms.

    Platforms:
    - bug_bounty: HackerOne, Bugcrowd, Intigriti, YesWeHack, Synack
    - dev_bounty: Gitcoin, GitHub Sponsors, Bountysource
    - data_annotation: Labelbox, Scale AI, Amazon Mechanical Turk
    """
    platforms = {
        "bug_bounty": {
            "name": "Bug Bounty",
            "platforms": ["HackerOne", "Bugcrowd", "Intigriti", "YesWeHack", "Synack"],
            "description": "Find vulnerabilities in software and get paid",
            "avg_reward": 500.0,
            "success_rate": 0.15,
            "skills": ["web security", "pentesting", "vulnerability analysis"],
            "connectors": ["hackerone", "bugcrowd", "intigriti", "yeswehack", "synack"],
        },
        "dev_bounty": {
            "name": "Dev Bounty",
            "platforms": ["Gitcoin", "GitHub Sponsors", "Bountysource", "IssueHunt"],
            "description": "Complete development tasks and get paid",
            "avg_reward": 150.0,
            "success_rate": 0.40,
            "skills": ["programming", "git", "development"],
            "connectors": ["gitcoin", "github"],
        },
        "data_annotation": {
            "name": "Data Annotation",
            "platforms": ["Labelbox", "Scale AI", "Amazon Mechanical Turk", "Figure Eight"],
            "description": "Annotate data for AI training and get paid",
            "avg_reward": 10.0,
            "success_rate": 0.85,
            "skills": ["data labeling", "annotation", "attention to detail"],
            "connectors": ["mechanical_turk"],
        },
    }

    return {"platforms": platforms}


@router.get("/sync/{platform}")
async def sync_platform_earnings(platform: str, api_key: str = "") -> dict[str, Any]:
    """Sync earnings from platform using existing connectors.

    Platforms:
    - hackerone: cores/platforms/hackerone.py
    - bugcrowd: cores/platforms/bugcrowd.py
    - intigriti: cores/platforms/intigriti.py
    - yeswehack: cores/platforms/yeswehack.py
    - synack: cores/platforms/synack.py
    """
    valid_platforms = ["hackerone", "bugcrowd", "intigriti", "yeswehack", "synack"]
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}",
        )

    try:
        # Import existing platform connector
        if platform == "hackerone":
            from cores.platforms.hackerone import HackerOne
            connector = HackerOne()
        elif platform == "bugcrowd":
            from cores.platforms.bugcrowd import Bugcrowd
            connector = Bugcrowd()
        elif platform == "intigriti":
            from cores.platforms.intigriti import Intigriti
            connector = Intigriti()
        elif platform == "yeswehack":
            from cores.platforms.yeswehack import YesWeHack
            connector = YesWeHack()
        elif platform == "synack":
            from cores.platforms.synack import Synack
            connector = Synack()
        else:
            raise HTTPException(status_code=400, detail="Platform not supported")

        # Sync earnings using existing connector
        sync_result = connector.sync_earnings(api_key)

        return {
            "success": sync_result.success,
            "earnings": sync_result.earnings,
            "payouts": sync_result.payouts,
            "programs": sync_result.programs,
            "total_earned": sync_result.total_earned,
            "total_pending": sync_result.total_pending,
            "error": sync_result.error,
        }

    except ImportError as e:
        logger.error(f"[ZERO-BARRIER] Platform connector not found: {e}")
        raise HTTPException(status_code=404, detail=f"Platform connector for {platform} not found")
    except Exception as e:
        logger.error(f"[ZERO-BARRIER] Error syncing platform: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/revenue-potential")
async def get_revenue_potential(include_market_modules: bool = True) -> dict[str, Any]:
    """Get maximum revenue potential analysis.

    Args:
        include_market_modules: Include trading, investment, and market intelligence modules (riskier but higher potential)

    Returns revenue potential across tiers:
    - conservative: 0.5x multiplier
    - moderate: 1.0x multiplier (recommended)
    - aggressive: 2.0x multiplier
    - maximum: 3.0x multiplier

    Base Platforms:
    - bug_bounty: HackerOne, Bugcrowd, Intigriti, YesWeHack, Synack
    - dev_bounty: Gitcoin, GitHub Sponsors, Bountysource
    - data_annotation: Labelbox, Scale AI, Amazon Mechanical Turk

    Market Modules (if enabled):
    - trading: Crypto Trading (cores/trading/executor.py)
    - investment: DeFi Yield Farming (cores/investment/manager.py)
    - market_intelligence: Market Intelligence Arbitrage (cores/market_intelligence/models.py)
    """
    try:
        report = generate_revenue_report(include_market_modules)
        return report
    except Exception as e:
        logger.error(f"[ZERO-BARRIER] Error generating revenue potential: {e}")
        raise HTTPException(status_code=500, detail=str(e))
