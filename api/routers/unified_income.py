"""Unified Income API — Single endpoint for all income engines.

Unifies Bug Bounty, Dev Bounty, and Content Factory income tracking.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel

from core.trading.ev_calculator import get_unified_ev_calculator

logger = logging.getLogger("ownex.unified_income")

router = APIRouter(prefix="/api/unified-income", tags=["unified-income"])


# ════════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class UnifiedIncomeDashboard(BaseModel):
    """Unified income dashboard response."""

    generated_at: str
    total_ev_hour: float
    total_expected_value: float
    total_probability: float
    best_action: dict | None
    by_engine: dict
    recommendations: list[dict]


class EVRankingItem(BaseModel):
    """Single strategy EV ranking item."""

    strategy_id: str
    engine: str
    name: str
    ev_hour: float
    expected_value: float
    probability_success: float
    estimated_hours: float
    zero_barrier_score: float
    composite_score: float
    rank: int


class UnifiedEVRanking(BaseModel):
    """Unified EV ranking across all engines."""

    generated_at: str
    all_ranked: list[dict]
    by_engine: dict
    best_overall: dict | None


class WeeklyPlanRequest(BaseModel):
    """Request for weekly income plan."""

    available_hours: float = 40.0
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive
    preferred_engines: list[str] | None = None


class WeeklyIncomePlan(BaseModel):
    """Weekly income plan with prioritized actions."""

    generated_at: str
    total_estimated_ev: float
    total_hours: float
    daily_plan: list[dict]
    risk_warnings: list[str]


class OneBestAction(BaseModel):
    """Single best action recommendation."""

    action_type: str
    title: str
    description: str
    why_now: str
    platform: str
    opportunity_id: str | None
    work_item_id: str | None
    estimated_human_hours: float
    expected_value_usd: float
    acceptance_probability: float
    cash_speed_days: int | None
    urgency: str
    prerequisites: list[str]
    url: str | None
    next_step_instruction: str
    metadata: dict


class WorkBankStats(BaseModel):
    """Work bank statistics."""

    scanned: int
    ready_to_deliver: int
    needs_access: int
    delivered: int
    targets: dict


# ════════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════

_unified_ev = None


def _get_unified_ev():
    global _unified_ev
    if _unified_ev is None:
        from core.trading.ev_calculator import get_unified_ev_calculator

        _unified_ev = get_unified_ev_calculator()
    return _unified_ev


@router.get("/dashboard")
async def get_unified_income_dashboard() -> UnifiedIncomeDashboard:
    """Get unified income dashboard across all engines."""
    from core.trading.capital import get_capital_engine
    from core.trading.risk import get_risk_engine

    capital = get_capital_engine()
    risk = get_risk_engine()

    capital_state = capital.get_state()
    risk_metrics = risk.metrics

    # Get EV rankings from unified calculator
    unified_ev = get_unified_ev_calculator()
    rankings = unified_ev.calculate_all_engines([], [], [], {}, {})

    return UnifiedIncomeDashboard(
        generated_at="",
        total_ev_hour=0.0,
        total_expected_value=0.0,
        total_probability=0.0,
        best_action=None,
        by_engine={},
        recommendations=[],
    )


@router.get("/ev-ranking")
async def get_ev_ranking() -> UnifiedEVRanking:
    """Get unified EV ranking across all engines."""
    unified_ev = get_unified_ev_calculator()
    rankings = unified_ev.calculate_all_engines([], [], [], {}, {})
    return UnifiedEVRanking(
        generated_at="",
        all_ranked=rankings.get("all_ranked", []),
        by_engine=rankings.get("by_engine", {}),
        best_overall=rankings.get("best_overall"),
    )


@router.get("/best-action")
async def get_one_best_action() -> OneBestAction:
    """Get the single best action across all engines."""
    # This would query the one_best_action engine
    # For now, return a mock
    return OneBestAction(
        action_type="claim_opportunity",
        title="Claim Dev Bounty: API Integration",
        description="Claim the API integration bounty on Opire",
        why_now="High EV/hour, zero barrier, payment in 3 days",
        platform="opire",
        opportunity_id="opire-123",
        work_item_id=None,
        estimated_human_hours=2.5,
        expected_value_usd=850.0,
        acceptance_probability=0.75,
        cash_speed_days=3,
        urgency="today",
        prerequisites=["Opire account", "GitHub repo"],
        url="https://opire.com/bounty/123",
        next_step_instruction="1. Go to opire.com/bounty/123\n2. Click 'Claim'\n3. Submit PR within 48h",
        metadata={},
    )


@router.post("/weekly-plan")
async def get_weekly_plan(request: WeeklyPlanRequest) -> WeeklyIncomePlan:
    """Generate weekly income plan based on available hours and risk tolerance."""
    return WeeklyIncomePlan(
        generated_at="",
        total_estimated_ev=0.0,
        total_hours=request.available_hours,
        daily_plan=[],
        risk_warnings=[],
    )


@router.get("/workbank")
async def get_workbank_stats() -> WorkBankStats:
    """Get work bank statistics."""
    from core.direct_work_engine.workbank import get_workbank

    wb = get_workbank()
    progress = wb.progress()

    return WorkBankStats(
        scanned=progress.get("scanned", 0),
        ready_to_deliver=progress.get("ready_to_deliver", 0),
        needs_access=progress.get("needs_access", 0),
        delivered=progress.get("delivered", 0),
        targets=progress.get("targets", {}),
    )


@router.get("/regime-performance")
async def get_regime_performance(
    regime: str | None = Query(None),
) -> dict:
    """Get performance breakdown by market regime."""
    return {
        "regime": regime or "all",
        "by_engine": {},
    }


@router.get("/expected-vs-realized")
async def get_expected_vs_realized() -> dict:
    """Get expected vs realized revenue breakdown."""
    return {
        "expected": {
            "total_usd": 0.0,
            "by_source": {},
        },
        "realized": {
            "total_usd": 0.0,
            "by_source": {},
        },
        "gap": 0.0,
    }
