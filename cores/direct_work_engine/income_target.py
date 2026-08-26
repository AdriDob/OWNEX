"""Income Target Engine — Set and track income goals with actionable plans.

Allows user to set weekly/monthly income targets and generates
an actionable plan to reach them based on available opportunities.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from cores.direct_work_engine.availability import get_available_hours
from cores.direct_work_engine.economic_engine import (
    OpportunityEconomicProfile,
    compute_economic_profile,
    get_economic_engine,
)
from cores.direct_work_engine.models import UserProfile
from cores.direct_work_engine.workbank import WorkItem

logger = logging.getLogger("ownex.income_target")


def workitem_to_opportunity(item: WorkItem) -> Any:
    """Convert WorkItem to Opportunity-like object for economic engine."""

    class MockOpp:
        pass

    opp = type("MockOpp", (), {})()
    opp.id = item.id
    opp.title = item.title
    opp.platform = item.platform
    opp.category = item.category
    opp.payment = float(item.reward or 0)
    opp.currency = "USDC"  # Use USDC for crypto payments
    opp.payment_method = "crypto"  # Default to crypto for now
    opp.company = ""
    opp.employment_type = item.employment_type if hasattr(item, "employment_type") else "bounty"
    opp.description = item.description if hasattr(item, "description") else ""
    opp.difficulty = 0.5
    opp.urgency = 0.5
    opp.source_confidence = 0.5
    opp.estimated_time_hours = getattr(item, "estimated_time_hours", 0.0)
    opp.requires_qualification = False
    opp.qualification_hours = 0.0
    opp.estimated_effort_hours = getattr(item, "estimated_time_hours", 0.0)
    opp.experience_required = "NONE"
    opp.portfolio_required = False
    opp.interview_required = False
    opp.technical_test_required = False
    opp.registration_required = False
    opp.time_to_payout_days = None
    opp.reputation = 0.5
    opp.risk = 0.5
    opp.payment_proven = False
    opp.stability = 0.5
    opp.compatibility = 0.5
    opp.accepts_beginner = True
    opp.accepts_freelancers = True
    opp.accepts_individuals = True
    opp.accepts_ai_tools = True
    opp.asynchronous = True
    opp.specialization = None
    opp.technology_tags = []
    opp.employment_type = getattr(item, "employment_type", "bounty")
    opp.hourly_rate_usd = None
    opp.time_to_first_work_hours = None
    opp.rate_source = "unknown"
    opp.entry_mechanism = "DIRECT"
    opp.experience_requirement = "NONE"
    opp.zero_barrier_score = None
    opp.international_payment = True  # Default to true for crypto payments
    return opp


class TargetTier(StrEnum):
    """Predefined income target tiers."""

    WEEKLY_100 = "weekly_100"
    WEEKLY_250 = "weekly_250"
    WEEKLY_500 = "weekly_500"
    WEEKLY_1000 = "weekly_1000"
    MONTHLY_1000 = "monthly_1000"
    MONTHLY_2500 = "monthly_2500"
    MONTHLY_5000 = "monthly_5000"
    MONTHLY_10000 = "monthly_10000"
    CUSTOM = "custom"


class TargetMode(StrEnum):
    """Target achievement mode."""

    FAST_CASH = "fast_cash"  # Prioritize quick payouts
    MAX_EV = "max_ev"  # Maximize expected value
    MAX_SUCCESS = "max_success"  # Maximize acceptance probability
    LOW_RISK = "low_risk"  # Minimize rejection risk
    BALANCED = "balanced"  # Balanced approach


@dataclass(slots=True)
class IncomeTarget:
    """User-defined income target."""

    tier: TargetTier
    amount_usd: float
    period: str  # "weekly" | "monthly"
    mode: TargetMode = TargetMode.BALANCED
    custom_amount: float | None = None
    custom_period: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    deadline: str | None = None


@dataclass(slots=True)
class TargetPlan:
    """Actionable plan to reach income target."""

    target: IncomeTarget
    required_opportunities: int
    required_hours_per_week: float
    required_hours_per_day: float
    recommended_sources: list[str]
    weekly_plan: list[dict[str, Any]]
    probability_of_success: float
    risk_factors: list[str]
    fallback_plan: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(slots=True)
class TargetProgress:
    """Current progress toward income target."""

    target: IncomeTarget
    earned_this_period: float
    pending_amount: float
    projected_total: float
    progress_pct: float
    days_remaining: int
    on_track: bool
    required_daily_rate: float
    actual_daily_rate: float
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class IncomeTargetEngine:
    """Engine for creating and tracking income targets."""

    def __init__(self) -> None:
        self._economic_engine = get_economic_engine()

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def create_target(
        self,
        tier: TargetTier,
        mode: TargetMode = TargetMode.BALANCED,
        custom_amount: float | None = None,
        custom_period: str | None = None,
    ) -> IncomeTarget:
        """Create an income target from tier or custom values."""
        if tier == TargetTier.CUSTOM:
            if custom_amount is None or custom_period is None:
                raise ValueError("Custom tier requires custom_amount and custom_period")
            return IncomeTarget(
                tier=TargetTier.CUSTOM,
                amount_usd=custom_amount,
                period=custom_period,
                mode=mode,
            )

        tier_config = _TIER_CONFIGS[tier]
        return IncomeTarget(
            tier=tier,
            amount_usd=tier_config["amount"],
            period=tier_config["period"],
            mode=mode,
        )

    def build_plan(self, target: IncomeTarget, profile: UserProfile | None = None) -> TargetPlan:
        """Build an actionable plan to reach the target."""
        # Get available opportunities
        from cores.direct_work_engine.workbank import get_workbank

        wb = get_workbank()
        work_items = list(wb._items.values())

        # Get economic profiles
        profiles = []
        for item in work_items:
            try:
                # Convert WorkItem to Opportunity-like object
                opp = workitem_to_opportunity(item)
                profile_data = compute_economic_profile(opp, profile)
                profiles.append(profile_data)
            except Exception:
                pass

        # Rank by target mode
        ranked = self._rank_by_mode(profiles, target.mode)

        # Calculate requirements
        target_amount = target.amount_usd
        period = target.period

        # Convert to weekly if monthly
        weekly_target = target_amount / 4.33 if period == "monthly" else target_amount

        # Filter feasible opportunities (within availability)
        # Use profile's availability_hours if provided, otherwise fall back to global engine
        if profile and profile.availability_hours is not None and profile.availability_hours >= 0:
            available_hours = profile.availability_hours
        else:
            available_hours = get_available_hours("this_week")
        feasible = [p for p in ranked if p.human_minutes and p.human_minutes / 60 <= available_hours]

        if not feasible:
            return TargetPlan(
                target=target,
                required_opportunities=0,
                required_hours_per_week=0,
                required_hours_per_day=0,
                recommended_sources=[],
                weekly_plan=[],
                probability_of_success=0.0,
                risk_factors=["No feasible opportunities within availability"],
            )

        # Calculate how many opportunities needed
        total_ev = sum(
            p.risk_adjusted_expected_value_per_user_hour * (p.human_minutes or 0) / 60 for p in feasible[:10]
        )
        if total_ev <= 0:
            return TargetPlan(
                target=target,
                required_opportunities=0,
                required_hours_per_week=0,
                required_hours_per_day=0,
                recommended_sources=[],
                weekly_plan=[],
                probability_of_success=0.0,
                risk_factors=["No positive EV opportunities"],
            )

        # Estimate opportunities needed
        avg_ev_per_opp = total_ev / len(feasible[:10])
        required_opps = max(1, int(weekly_target / avg_ev_per_opp) + 1)

        # Required hours
        top_feasible = feasible[:required_opps]
        required_hours = sum(p.human_minutes or 0 for p in top_feasible) / 60

        # Build weekly plan
        weekly_plan = self._build_weekly_plan(top_feasible, target)

        # Probability of success
        success_prob = sum(p.acceptance_probability or 0.5 for p in top_feasible) / len(top_feasible)

        # Risk factors
        risk_factors = []
        if required_hours > get_available_hours("this_week"):
            risk_factors.append("Required hours exceed available hours")
        if success_prob < 0.5:
            risk_factors.append("Low acceptance probability")
        if len(set(p.platform for p in top_feasible)) == 1:
            risk_factors.append("Single platform dependency")

        return TargetPlan(
            target=target,
            required_opportunities=required_opps,
            required_hours_per_week=round(required_hours, 1),
            required_hours_per_day=round(required_hours / 5, 1),
            recommended_sources=list(set(p.platform for p in top_feasible)),
            weekly_plan=weekly_plan,
            probability_of_success=round(success_prob, 2),
            risk_factors=risk_factors,
            fallback_plan="Reduce target tier or extend deadline" if risk_factors else None,
        )

    def track_progress(self, target: IncomeTarget) -> TargetProgress:
        """Track current progress toward target."""
        from cores.direct_work_engine.workbank import get_workbank
        from cores.revenue_tracker.revenue_tracker import get_revenue_tracker

        wb = get_workbank()
        tracker = get_revenue_tracker()

        # Earned this period
        earned = 0.0
        pending = 0.0

        # From WorkBank delivered items
        for item in wb._items.values():
            if item.status == "delivered":
                earned += item.reward
            elif item.status == "ready_to_deliver":
                pending += item.reward

        # From RevenueTracker
        if tracker:
            try:
                opportunities = tracker.get_all_opportunities() if hasattr(tracker, "get_all_opportunities") else []
                for opp in opportunities:
                    if getattr(opp, "status", "") == "paid":
                        earned += getattr(opp, "payout_amount", 0) or getattr(opp, "payment", 0)
                    elif getattr(opp, "status", "") in ("accepted", "submitted"):
                        pending += getattr(opp, "payout_amount", 0) or getattr(opp, "payment", 0)
            except Exception:
                pass

        # Progress calculation
        period_amount = target.amount_usd if target.period == "weekly" else target.amount_usd

        progress_pct = min(100.0, (earned / period_amount * 100) if period_amount > 0 else 0)

        # Days remaining
        now = datetime.now(UTC)
        if target.period == "weekly":
            # Week ends Sunday
            days_remaining = (6 - now.weekday()) % 7 + 1
        else:
            # Month ends last day
            next_month = now.replace(day=28) + timedelta(days=4)
            days_remaining = (next_month - timedelta(days=next_month.day)).day

        on_track = (earned + pending) >= (
            target.amount_usd * 0.8 * (1 - days_remaining / (7 if target.period == "weekly" else 30))
        )

        return TargetProgress(
            target=target,
            earned_this_period=earned,
            pending_amount=pending,
            projected_total=earned + pending,
            progress_pct=round(progress_pct, 1),
            days_remaining=days_remaining,
            on_track=on_track,
            required_daily_rate=round(target.amount_usd / (7 if target.period == "weekly" else 30), 2),
            actual_daily_rate=round(earned / max(1, (7 if target.period == "weekly" else 30) - days_remaining), 2),
        )

    # ──────────────────────────────────────────────────────────────────
    # Internals
    # ──────────────────────────────────────────────────────────────────

    def _rank_by_mode(
        self, profiles: list[OpportunityEconomicProfile], mode: TargetMode
    ) -> list[OpportunityEconomicProfile]:
        if mode == TargetMode.FAST_CASH:
            return sorted(profiles, key=lambda p: p.cash_adjusted_value or 0, reverse=True)
        elif mode == TargetMode.MAX_EV:
            return sorted(profiles, key=lambda p: p.expected_net_value, reverse=True)
        elif mode == TargetMode.MAX_SUCCESS:
            return sorted(profiles, key=lambda p: p.acceptance_probability or 0, reverse=True)
        elif mode == TargetMode.LOW_RISK:
            return sorted(profiles, key=lambda p: -len(p.risk_factors))
        else:  # BALANCED
            return sorted(profiles, key=lambda p: p.risk_adjusted_expected_value_per_user_hour, reverse=True)

    def _build_weekly_plan(self, profiles: list[OpportunityEconomicProfile], target: IncomeTarget) -> list[dict]:
        """Build day-by-day weekly plan."""
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        plan = []

        # Distribute profiles across week
        for i, profile in enumerate(profiles[:7]):
            day_idx = i % 7
            day = days[day_idx]
            (profile.human_minutes or 0) / 60

            plan.append(
                {
                    "day": day,
                    "action": profile.next_action or f"Work on {profile.platform}",
                    "platform": profile.platform,
                    "expected_ev": round(
                        profile.risk_adjusted_expected_value_per_user_hour * (profile.human_minutes or 0) / 60, 2
                    ),
                    "hours": round(profile.human_minutes / 60, 1) if profile.human_minutes else 0,
                    "cash_speed_days": profile.payment_delay_days,
                    "acceptance_prob": profile.acceptance_probability,
                }
            )

        # Fill remaining days
        for i in range(len(profiles), 7):
            day = days[i]
            plan.append(
                {
                    "day": day,
                    "action": "Review pipeline / prep next week",
                    "platform": "internal",
                    "expected_ev": 0,
                    "hours": 1.0,
                    "cash_speed_days": None,
                    "acceptance_prob": None,
                }
            )

        return plan


# ──────────────────────────────────────────────────────────────────────
# Tier Configurations
# ──────────────────────────────────────────────────────────────────────

_TIER_CONFIGS: dict[str, dict] = {
    "weekly_100": {"amount": 100.0, "period": "weekly"},
    "weekly_250": {"amount": 250.0, "period": "weekly"},
    "weekly_500": {"amount": 500.0, "period": "weekly"},
    "weekly_1000": {"amount": 1000.0, "period": "weekly"},
    "monthly_1000": {"amount": 1000.0, "period": "monthly"},
    "monthly_2500": {"amount": 2500.0, "period": "monthly"},
    "monthly_5000": {"amount": 5000.0, "period": "monthly"},
    "monthly_10000": {"amount": 10000.0, "period": "monthly"},
}


# ──────────────────────────────────────────────────────────────────────
# Convenience
# ──────────────────────────────────────────────────────────────────────

_income_target_engine: IncomeTargetEngine | None = None


def get_income_target_engine() -> IncomeTargetEngine:
    global _income_target_engine
    if _income_target_engine is None:
        _income_target_engine = IncomeTargetEngine()
    return _income_target_engine


def create_income_target(
    tier: TargetTier,
    mode: TargetMode = TargetMode.BALANCED,
    custom_amount: float | None = None,
    custom_period: str | None = None,
) -> IncomeTarget:
    return get_income_target_engine().create_target(tier, mode, custom_amount, None)


def build_target_plan(target: IncomeTarget, profile: UserProfile | None = None) -> TargetPlan:
    return get_income_target_engine().build_plan(target, profile)


def track_target_progress(target: IncomeTarget) -> TargetProgress:
    return get_income_target_engine().track_progress(target)
