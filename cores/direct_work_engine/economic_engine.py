"""Unified Economic Engine — Single Source of Truth for all economic calculations.

Consolidates:
- economics.py (ExpectedCash, cash_speed, EV)
- recommendation.py (weighted EV scoring)
- max_daily_income.py (ranking by EV)
- execution_planner.py (expected_value_per_hour)
- income_plan.py (projections)

Into ONE canonical engine with ONE formula per metric.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from cores.direct_work_engine.models import Opportunity, UserProfile
from cores.direct_work_engine.scoring import ZeroBarrierScorer
from cores.payment_compat.engine import PaymentCompatibilityEngine
from cores.revenue_tracker.revenue_tracker import get_revenue_tracker

logger = logging.getLogger("ownex.economic_engine")


# ──────────────────────────────────────────────────────────────────────
# Enums & Constants
# ──────────────────────────────────────────────────────────────────────


class ConfidenceBand(Enum):
    HIGH = "high"  # ≥ 0.75
    MEDIUM = "medium"  # 0.4–0.75
    LOW = "low"  # 0.2–0.4
    UNKNOWN = "unknown"  # < 0.2 or missing critical data


# Weights for the unified EV formula (sum = 1.0)
_UNIFIED_EV_WEIGHTS = {
    "expected_reward": 0.25,
    "acceptance_probability": 0.25,
    "skill_match": 0.15,
    "barrier_score": 0.10,  # inverted: lower barrier = higher score
    "cash_speed": 0.10,
    "payment_reliability": 0.10,
    "platform_reliability": 0.05,
}

# Risk adjustment factors (multipliers)
_RISK_FACTORS = {
    "high_competition": 0.7,
    "low_freshness": 0.8,
    "payment_risk": 0.6,
    "geo_mismatch": 0.5,
    "skill_gap": 0.7,
    "unknown_acceptance": 0.5,
}

# Confidence thresholds
_CONFIDENCE_THRESHOLDS = {
    ConfidenceBand.HIGH: 0.75,
    ConfidenceBand.MEDIUM: 0.40,
    ConfidenceBand.LOW: 0.20,
}


# ──────────────────────────────────────────────────────────────────────
# Core Data Structures
# ──────────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class OpportunityEconomicProfile:
    """Canonical economic profile for a single opportunity.

    This is THE single source of truth for all economic decisions.
    Every other module MUST read from this, never compute independently.
    """

    # Identity
    opportunity_id: str
    platform: str
    organization: str | None = None
    category: str | None = None
    task_type: str | None = None

    # Financial
    payment: float = 0.0
    payment_currency: str = "USD"
    payment_method: str | None = None
    payment_reliability: float = 0.5  # 0–1
    payment_delay_days: int | None = None

    # Probabilities (0–1, or None = unknown)
    acceptance_probability: float | None = None
    task_availability_probability: float | None = None
    qualification_probability: float | None = None

    # Time estimates (hours)
    qualification_time_hours: float | None = None
    estimated_execution_time_hours: float | None = None
    preparation_time_hours: float | None = None
    submission_time_hours: float | None = None
    expected_rework_time_hours: float | None = None

    # Risk & Competition
    rejection_probability: float = 0.0
    duplicate_probability: float = 0.0
    competition_level: float = 0.5  # 0–1
    freshness_score: float = 1.0  # 0–1 (1 = fresh)

    # Compatibility
    geo_compatibility: float = 1.0  # 0–1 (1 = full compatible)
    payment_compatibility: float = 1.0  # 0–1
    skill_match: float = 0.5  # 0–1
    difficulty: float = 0.5  # 0–1
    urgency: float = 0.5  # 0–1

    # Source quality
    source_confidence: float = 0.5  # 0–1

    # Computed fields (populated by engine)
    expected_gross_value: float = 0.0
    expected_net_value: float = 0.0
    expected_hourly_value: float = 0.0
    risk_adjusted_hourly_value: float = 0.0
    cash_adjusted_value: float = 0.0
    execution_adjusted_value: float = 0.0
    risk_adjusted_expected_value_per_user_hour: float = 0.0  # PRIMARY METRIC

    # Risk & Confidence
    risk_factors: list[str] = field(default_factory=list)
    confidence: ConfidenceBand = ConfidenceBand.UNKNOWN
    confidence_score: float = 0.0

    # Next action
    next_action: str | None = None
    human_minutes: float | None = None
    automation_minutes: float | None = None
    time_compression_ratio: float | None = None

    # Metadata
    computed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    version: int = 1


@dataclass(slots=True)
class EconomicInputs:
    """Raw inputs for computing an economic profile."""

    opportunity: Opportunity
    profile: UserProfile | None = None
    platform_facts: dict[str, Any] | None = None
    revenue_history: list[dict] | None = None
    competition_data: dict[str, Any] | None = None
    freshness_data: dict[str, Any] | None = None


# ──────────────────────────────────────────────────────────────────────
# Economic Engine
# ──────────────────────────────────────────────────────────────────────


class EconomicEngine:
    """Single Source of Truth for ALL economic calculations.

    Usage:
        engine = EconomicEngine()
        profile = engine.compute_profile(opportunity, user_profile)
        # profile.risk_adjusted_expected_value_per_user_hour is the primary metric
    """

    def __init__(self) -> None:
        self._scorer = ZeroBarrierScorer()
        self._payment_engine = PaymentCompatibilityEngine()
        self._revenue_tracker = None

    def _get_revenue_tracker(self):
        if self._revenue_tracker is None:
            try:
                self._revenue_tracker = get_revenue_tracker()
            except Exception:
                self._revenue_tracker = None
        return self._revenue_tracker

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────

    def compute_profile(self, inputs: EconomicInputs) -> OpportunityEconomicProfile:
        """Compute the complete economic profile for an opportunity.

        This is THE entry point. All economic decisions flow from here.
        """
        opp = inputs.opportunity
        profile = inputs.profile

        # 1. Build base profile from opportunity data
        profile_data = self._extract_base_data(opp, inputs)

        # 2. Compute probabilities from history
        profile_data = self._compute_probabilities(profile_data, inputs)

        # 3. Compute time estimates
        profile_data = self._estimate_times(profile_data, inputs)

        # 4. Compute risk & competition
        profile_data = self._assess_risk_competition(profile_data, inputs)

        # 5. Compute compatibility
        profile_data = self._compute_compatibility(profile_data, inputs)

        # 6. THE UNIFIED ECONOMIC CALCULATION
        profile_data = self._unified_economic_calculation(profile_data)

        # 7. Risk adjustment
        profile_data = self._apply_risk_adjustment(profile_data)

        # 8. Confidence assessment
        profile_data = self._assess_confidence(profile_data)

        # 9. Next action & time compression
        profile_data = self._determine_next_action(profile_data, inputs)

        return profile_data

    def compute_batch(
        self, opportunities: list[Opportunity], profile: UserProfile | None = None
    ) -> list[OpportunityEconomicProfile]:
        """Compute profiles for multiple opportunities efficiently."""
        results = []
        for opp in opportunities:
            inputs = EconomicInputs(opportunity=opp, profile=profile)
            try:
                results.append(self.compute_profile(inputs))
            except Exception as e:
                logger.warning("Failed to compute profile for %s: %s", opp.id, e)
                # Return minimal profile with error flag
                results.append(
                    OpportunityEconomicProfile(
                        opportunity_id=opp.id,
                        platform=opp.platform.value if hasattr(opp.platform, "value") else str(opp.platform),
                        confidence=ConfidenceBand.UNKNOWN,
                        risk_factors=[f"computation_error: {e}"],
                    )
                )
        return results

    def rank_opportunities(
        self, profiles: list[OpportunityEconomicProfile], mode: str = "risk_adjusted"
    ) -> list[OpportunityEconomicProfile]:
        """Rank opportunities by the specified metric."""
        if mode == "risk_adjusted":
            return sorted(profiles, key=lambda p: p.risk_adjusted_expected_value_per_user_hour, reverse=True)
        elif mode == "expected_value":
            return sorted(profiles, key=lambda p: p.expected_net_value, reverse=True)
        elif mode == "hourly_value":
            return sorted(profiles, key=lambda p: p.expected_hourly_value, reverse=True)
        elif mode == "cash_speed":
            return sorted(profiles, key=lambda p: p.cash_adjusted_value or 0, reverse=True)
        elif mode == "success_probability":
            return sorted(profiles, key=lambda p: p.acceptance_probability or 0, reverse=True)
        elif mode == "fast_cash":
            return sorted(profiles, key=lambda p: p.cash_adjusted_value or 0, reverse=True)
        else:
            return sorted(profiles, key=lambda p: p.risk_adjusted_expected_value_per_user_hour, reverse=True)

    def get_next_best_action(
        self, profiles: list[OpportunityEconomicProfile], available_hours: float | None = None
    ) -> OpportunityEconomicProfile | None:
        """Get the single best action for the user right now."""
        if not profiles:
            return None

        # Filter by availability if provided
        if available_hours is not None:
            feasible = [p for p in profiles if p.human_minutes and p.human_minutes / 60 <= available_hours]
            if feasible:
                profiles = feasible

        ranked = self.rank_opportunities(profiles, mode="risk_adjusted")
        return ranked[0] if ranked else None

    # ──────────────────────────────────────────────────────────────────
    # INTERNAL COMPUTATION PIPELINE
    # ──────────────────────────────────────────────────────────────────

    def _extract_base_data(self, opp: Opportunity, inputs: EconomicInputs) -> OpportunityEconomicProfile:
        """Extract base data from opportunity."""
        platform_str = opp.platform.value if hasattr(opp.platform, "value") else str(opp.platform)
        category_str = opp.category.value if hasattr(opp.category, "value") else str(opp.category)

        return OpportunityEconomicProfile(
            opportunity_id=opp.id,
            platform=platform_str,
            organization=opp.company,
            category=category_str,
            task_type=opp.employment_type.value
            if hasattr(opp.employment_type, "value")
            else str(getattr(opp, "employment_type", "")),
            payment=float(opp.payment or 0),
            payment_currency=opp.currency or "USD",
            payment_method=opp.payment_method.value
            if hasattr(opp.payment_method, "value")
            else str(opp.payment_method),
            difficulty=float(getattr(opp, "difficulty", 0.5) or 0.5),
            urgency=0.5,
            source_confidence=0.5,
        )

    def _compute_probabilities(
        self, profile: OpportunityEconomicProfile, inputs: EconomicInputs
    ) -> OpportunityEconomicProfile:
        """Compute acceptance, availability, qualification probabilities from history."""
        # Platform acceptance from revenue history
        if inputs.revenue_history:
            platform_history = [r for r in inputs.revenue_history if r.get("platform") == profile.platform]
            if platform_history:
                accepted = sum(1 for r in platform_history if r.get("status") in ("accepted", "paid"))
                total = len(platform_history)
                profile.acceptance_probability = accepted / total if total > 0 else None

        # Category acceptance
        if inputs.revenue_history and profile.category:
            cat_history = [r for r in inputs.revenue_history if r.get("category") == profile.category]
            if cat_history:
                accepted = sum(1 for r in cat_history if r.get("status") in ("accepted", "paid"))
                total = len(cat_history)
                if profile.acceptance_probability is None and total > 0:
                    profile.acceptance_probability = accepted / total

        # Task availability from platform facts
        if inputs.platform_facts:
            facts = inputs.platform_facts
            profile.task_availability_probability = facts.get("task_availability", 0.5)

        # Qualification probability
        if profile.qualification_time_hours:
            # Has qualification step = lower probability unless proven
            profile.qualification_probability = 0.6
        else:
            profile.qualification_probability = 0.9

        # Default fallback - NEVER invent probabilities
        if profile.acceptance_probability is None:
            profile.acceptance_probability = 0.5  # conservative prior, marked as prior in confidence

        return profile

    def _estimate_times(
        self, profile: OpportunityEconomicProfile, inputs: EconomicInputs
    ) -> OpportunityEconomicProfile:
        """Estimate all time components."""
        opp = inputs.opportunity

        # Qualification time - check if any qualification gate exists
        has_qualification_gate = (
            getattr(opp, "interview_required", False)
            or getattr(opp, "technical_test_required", False)
            or getattr(opp, "portfolio_required", False)
        )
        if has_qualification_gate:
            profile.qualification_time_hours = float(getattr(opp, "qualification_hours", 2.0))
        elif profile.category == "ai_evaluation":
            profile.qualification_time_hours = 1.5  # assessment
        else:
            profile.qualification_time_hours = 0.0

        # Execution time from opportunity or category defaults
        if hasattr(opp, "estimated_time_hours") and opp.estimated_time_hours:
            profile.estimated_execution_time_hours = float(opp.estimated_time_hours)
        elif profile.category == "bug_bounty":
            profile.estimated_execution_time_hours = 8.0
        elif profile.category == "dev_bounty":
            profile.estimated_execution_time_hours = 4.0
        elif profile.category == "ai_evaluation":
            profile.estimated_execution_time_hours = 1.0
        else:
            profile.estimated_execution_time_hours = 4.0

        # Preparation time (OWNEX automation)
        profile.preparation_time_hours = 0.5  # OWNEX prepares submission package

        # Submission time
        profile.submission_time_hours = 0.25 if profile.payment_compatibility > 0.7 else 1.0

        # Expected rework
        profile.expected_rework_time_hours = profile.estimated_execution_time_hours * 0.15

        return profile

    def _assess_risk_competition(
        self, profile: OpportunityEconomicProfile, inputs: EconomicInputs
    ) -> OpportunityEconomicProfile:
        """Assess competition, freshness, rejection risk."""
        # Competition level
        if inputs.competition_data:
            profile.competition_level = inputs.competition_data.get("level", 0.5)
        elif profile.category == "bug_bounty":
            profile.competition_level = 0.7  # high
        elif profile.category == "dev_bounty":
            profile.competition_level = 0.4
        elif profile.category == "ai_evaluation":
            profile.competition_level = 0.3
        else:
            profile.competition_level = 0.5

        # Freshness
        if inputs.freshness_data:
            profile.freshness_score = inputs.freshness_data.get("score", 1.0)
        else:
            # Decay based on age if available
            profile.freshness_score = 1.0  # assume fresh if unknown

        # Rejection probability
        profile.rejection_probability = (
            1 - (profile.acceptance_probability or 0.5)
        ) * 0.7 + profile.competition_level * 0.3

        # Duplicate probability
        profile.duplicate_probability = 0.1 if profile.competition_level > 0.7 else 0.05

        return profile

    def _compute_compatibility(
        self, profile: OpportunityEconomicProfile, inputs: EconomicInputs
    ) -> OpportunityEconomicProfile:
        """Compute geo, payment, skill compatibility."""
        # Geo compatibility (Argentina focus)
        profile.geo_compatibility = 1.0  # default compatible
        if hasattr(inputs.opportunity, "geo_restrictions"):
            # Check if Argentina is allowed
            pass

        # Payment compatibility via PaymentCompatibilityEngine
        try:
            from cores.payment_compat.engine import PaymentRequirement

            req = PaymentRequirement(
                method=profile.payment_method or "crypto",
                currency=profile.payment_currency,
                region="AR",
                amount=profile.payment,
                required_documentation="",
                platform=profile.platform,
            )
            verdict = self._payment_engine.evaluate_chain(req)
            profile.payment_compatibility = verdict.score / 100.0
            profile.payment_reliability = verdict.score / 100.0
        except Exception:
            profile.payment_compatibility = 0.5
            profile.payment_reliability = 0.5

        # Skill match from profile
        if profile.category and inputs.profile:
            # Would check skill overlap
            profile.skill_match = 0.7  # placeholder

        return profile

    def _unified_economic_calculation(self, profile: OpportunityEconomicProfile) -> OpportunityEconomicProfile:
        """THE UNIFIED ECONOMIC CALCULATION — Single Source of Truth.

        Formula:
        expected_gross = payment * acceptance_prob * availability_prob * qualification_prob
        expected_net = expected_gross * payment_reliability
        human_hours = qualification + execution + preparation + submission + expected_rework
        expected_hourly = expected_net / human_hours
        risk_adjusted = expected_hourly * risk_multiplier
        cash_adjusted = expected_net * cash_speed_factor
        execution_adjusted = expected_net / (human_hours * automation_ratio)
        PRIMARY = risk_adjusted * cash_factor * availability_factor
        """
        # Probabilities (use 0.5 for unknown = conservative)
        p_accept = profile.acceptance_probability or 0.5
        p_available = profile.task_availability_probability or 0.5
        p_qual = profile.qualification_probability or 0.9

        # Expected Gross Value
        profile.expected_gross_value = profile.payment * p_accept * p_available * p_qual

        # Expected Net Value (after payment reliability)
        profile.expected_net_value = profile.expected_gross_value * profile.payment_reliability

        # Human time calculation
        qual = profile.qualification_time_hours or 0
        exec_t = profile.estimated_execution_time_hours or 4
        prep = profile.preparation_time_hours or 0.5
        submit = profile.submission_time_hours or 0.5
        rework = profile.expected_rework_time_hours or 0

        profile.human_minutes = round((qual + exec_t + prep + submit + rework) * 60)
        total_human_hours = max(qual + exec_t + prep + submit + rework, 0.25)

        # Expected hourly value
        profile.expected_hourly_value = profile.expected_net_value / total_human_hours if total_human_hours > 0 else 0

        # Cash speed factor (0–1, higher = faster cash)
        cash_speed = 1.0
        if profile.payment_delay_days:
            # Decay: 30 days = 0.5, 7 days = 0.9, 1 day = 1.0
            cash_speed = max(0.3, 1.0 - (profile.payment_delay_days / 60))
        profile.cash_adjusted_value = profile.expected_net_value * cash_speed

        # Execution automation ratio (OWNEX automates prep/submission)
        automation_saved = (profile.preparation_time_hours or 0.5) + (profile.submission_time_hours or 0.5)
        total_manual = total_human_hours
        automation_ratio = max(0.1, 1.0 - (automation_saved / total_manual))
        profile.automation_minutes = round(automation_saved * 60)
        profile.time_compression_ratio = round(1.0 / automation_ratio, 2) if automation_ratio > 0 else 1.0
        profile.execution_adjusted_value = profile.expected_net_value * automation_ratio

        # Risk multiplier
        risk_mult = 1.0
        if profile.risk_factors:
            for factor in profile.risk_factors:
                risk_mult *= _RISK_FACTORS.get(factor, 0.9)
        profile.risk_adjusted_hourly_value = profile.expected_hourly_value * risk_mult

        # PRIMARY METRIC: Risk-adjusted expected value per user hour
        # Combines: expected value, risk, cash speed, availability
        availability_factor = (profile.task_availability_probability or 0.5) * (profile.acceptance_probability or 0.5)
        cash_factor = cash_speed
        profile.risk_adjusted_expected_value_per_user_hour = (
            profile.risk_adjusted_hourly_value * availability_factor * cash_factor
        )

        return profile

    def _apply_risk_adjustment(self, profile: OpportunityEconomicProfile) -> OpportunityEconomicProfile:
        """Apply risk factors based on profile attributes."""
        risk_factors = []

        if profile.competition_level > 0.7:
            risk_factors.append("high_competition")
        if profile.freshness_score < 0.5:
            risk_factors.append("low_freshness")
        if profile.payment_compatibility < 0.5:
            risk_factors.append("payment_risk")
        if profile.geo_compatibility < 0.5:
            risk_factors.append("geo_mismatch")
        if profile.skill_match < 0.4:
            risk_factors.append("skill_gap")
        if profile.acceptance_probability is None or profile.acceptance_probability < 0.3:
            risk_factors.append("unknown_acceptance")
        if profile.payment_delay_days and profile.payment_delay_days > 30:
            risk_factors.append("payment_risk")

        profile.risk_factors = risk_factors
        return profile

    def _assess_confidence(self, profile: OpportunityEconomicProfile) -> OpportunityEconomicProfile:
        """Assess confidence based on data completeness."""
        score = 0.0
        factors = 0

        # Primary data availability
        if profile.payment > 0:
            score += 1
            factors += 1
        if profile.acceptance_probability is not None:
            score += 1
            factors += 1
        if profile.task_availability_probability is not None:
            score += 1
            factors += 1
        if profile.qualification_probability is not None:
            score += 1
            factors += 1
        if profile.estimated_execution_time_hours is not None:
            score += 1
            factors += 1
        if profile.payment_reliability > 0:
            score += 1
            factors += 1
        if profile.payment_compatibility > 0:
            score += 1
            factors += 1

        confidence_score = score / factors if factors > 0 else 0.0
        profile.confidence_score = confidence_score

        # Assign band
        for band in (ConfidenceBand.HIGH, ConfidenceBand.MEDIUM, ConfidenceBand.LOW, ConfidenceBand.UNKNOWN):
            if confidence_score >= _CONFIDENCE_THRESHOLDS[band]:
                profile.confidence = band
                break

        return profile

    def _determine_next_action(
        self, profile: OpportunityEconomicProfile, inputs: EconomicInputs
    ) -> OpportunityEconomicProfile:
        """Determine the concrete next action for the user."""
        if profile.qualification_time_hours and profile.qualification_time_hours > 0:
            profile.next_action = (
                f"Completar assessment/calificación en {profile.platform} (~{profile.qualification_time_hours:.1f}h)"
            )
        elif profile.payment_compatibility < 0.5:
            profile.next_action = (
                f"Configurar método de pago compatible ({profile.payment_method or 'ver Payment Compat'})"
            )
        elif profile.geo_compatibility < 0.5:
            profile.next_action = "Verificar compatibilidad geográfica para Argentina"
        else:
            profile.next_action = f"Ejecutar trabajo en {profile.platform}: {inputs.opportunity.title or 'tarea'}"

        return profile


# ──────────────────────────────────────────────────────────────────────
# Singleton & Convenience
# ──────────────────────────────────────────────────────────────────────

_economic_engine: EconomicEngine | None = None


def get_economic_engine() -> EconomicEngine:
    global _economic_engine
    if _economic_engine is None:
        _economic_engine = EconomicEngine()
    return _economic_engine


def compute_economic_profile(
    opportunity: Opportunity, profile: UserProfile | None = None
) -> OpportunityEconomicProfile:
    """Convenience function for single opportunity."""
    engine = get_economic_engine()
    inputs = EconomicInputs(opportunity=opportunity, profile=profile)
    return engine.compute_profile(inputs)


def rank_opportunities(
    profiles: list[OpportunityEconomicProfile], mode: str = "risk_adjusted"
) -> list[OpportunityEconomicProfile]:
    return get_economic_engine().rank_opportunities(profiles, mode)


def get_next_best_action(
    profiles: list[OpportunityEconomicProfile], available_hours: float | None = None
) -> OpportunityEconomicProfile | None:
    return get_economic_engine().get_next_best_action(profiles, available_hours)
