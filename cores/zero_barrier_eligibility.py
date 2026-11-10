#!/usr/bin/env python3
"""OWNEX Zero-Barrier Eligibility Engine.

Automatically assesses sources and opportunities for zero-barrier access.
No interview, portfolio, or experience required. Uses criteria-based classification.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("ownex.zero_barrier_eligibility")

__all__ = [
    "BarrierType",
    "EligibilityStatus",
    "ZeroBarrierCriteria",
    "EligibilityAssessment",
    "ZeroBarrierEligibilityEngine",
    "get_eligibility_engine",
    "assess_source_zero_barrier",
    "assess_opportunity_zero_barrier",
    "assess_source_with_verification",
]


class BarrierType(Enum):
    """Barrier types that can disqualify from zero-barrier access."""

    INTERVIEW = "interview"
    PORTFOLIO = "portfolio"
    EXPERIENCE = "experience"
    DEGREE = "degree"
    CERTIFICATION = "certification"


class EligibilityStatus(Enum):
    """Eligibility status for zero-barrier access."""

    APPROVED = "approved"  # Zero-barrier: no interview/portfolio/experience required
    CONDITIONAL = "conditional"  # Minimal barrier: simple onboarding required
    EXPERIENCE_REQUIRED = "experience_required"  # Requires proven experience
    INTERVIEW_REQUIRED = "interview_required"  # Requires interview process
    DEGREE_REQUIRED = "degree_required"  # Requires formal degree


@dataclass
class ZeroBarrierCriteria:
    """Criteria for zero-barrier eligibility assessment."""

    # Barrier types that disqualify from zero-barrier
    forbidden_barriers: list[BarrierType] = field(
        default_factory=lambda: [
            BarrierType.INTERVIEW,
            BarrierType.PORTFOLIO,
            BarrierType.EXPERIENCE,
            BarrierType.DEGREE,
            BarrierType.CERTIFICATION,
        ]
    )

    # Minimum skill level required (beginner-friendly)
    max_difficulty: str = "beginner"  # beginner, intermediate, advanced, expert

    # Acceptable domains for zero-barrier access
    acceptable_domains: list[str] = field(
        default_factory=lambda: [
            "bug_bounty",
            "dev_bounty",
            "data_annotation",
            "ai_training",
            "survey",
            "usertesting",
        ]
    )

    # Maximum time investment per day (hours)
    max_daily_hours: float = 8.0

    # Minimum success rate threshold (0-1)
    min_success_rate: float = 0.15


@dataclass
class EligibilityAssessment:
    """Result of zero-barrier eligibility assessment."""

    source_id: str
    eligibility: EligibilityStatus
    barriers_identified: list[BarrierType]
    recommended_actions: list[str]
    difficulty: str
    estimated_earnings_potential: float
    onboarding_time_minutes: int
    metadata: dict[str, Any] = field(default_factory=dict)


class ZeroBarrierEligibilityEngine:
    """Engine for automated zero-barrier eligibility assessment.

    Evaluates sources and opportunities against criteria to determine
    if they qualify for zero-barrier access (no interview, portfolio, or
    experience required).
    """

    def __init__(self, criteria: ZeroBarrierCriteria | None = None):
        self.criteria = criteria or ZeroBarrierCriteria()
        self._assessment_cache: dict[str, EligibilityAssessment] = {}

    def assess_source(self, source_id: str, source_data: dict[str, Any]) -> EligibilityAssessment:
        """Assess a source for zero-barrier eligibility.

        Args:
            source_id: Unique identifier for the source
            source_data: Source metadata including domain, barriers, requirements

        Returns:
            EligibilityAssessment with status and recommendations
        """
        barriers_identified: list[BarrierType] = []
        difficulty = "beginner"
        onboarding_minutes = 5
        estimated_earnings = 0.0
        eligibility = EligibilityStatus.APPROVED
        recommended_actions: list[str] = []

        # Check for forbidden barriers
        platform = source_data.get("platform", "unknown")
        barriers_raw = source_data.get("barriers", [])

        for barrier_raw in barriers_raw:
            try:
                barrier = BarrierType(barrier_raw)
                if barrier in self.criteria.forbidden_barriers:
                    barriers_identified.append(barrier)
                    eligibility = EligibilityStatus.INTERVIEW_REQUIRED
            except ValueError:
                # Unknown barrier type, treat as conditional
                pass

        # If no forbidden barriers found, check other criteria
        if not barriers_identified:
            # Check difficulty
            difficulty_raw = source_data.get("difficulty", "beginner")
            difficulty = difficulty_raw

            if difficulty in ["advanced", "expert"] and self.criteria.max_difficulty == "beginner":
                # High difficulty but max allowed is beginner
                eligibility = EligibilityStatus.CONDITIONAL
                recommended_actions.append(f"Recommended: Start with beginner-level {platform} tasks")
                onboarding_minutes = 30
                estimated_earnings = 15.0
            else:
                eligibility = EligibilityStatus.APPROVED
                onboarding_minutes = 5
                # Estimate earnings based on platform and success rate
                estimated_earnings = self._estimate_earnings(platform, source_data)

            # Check domain acceptability
            if platform not in self.criteria.acceptable_domains:
                eligibility = EligibilityStatus.CONDITIONAL
                recommended_actions.append(f"Domain '{platform}' not in default zero-barrier list; manual review required")

        # If we have barriers identified but not forbidden
        if barriers_identified and eligibility == EligibilityStatus.APPROVED:
            eligibility = EligibilityStatus.CONDITIONAL
            recommended_actions.append("Some barriers detected; conditional approval with onboarding")

        assessment = EligibilityAssessment(
            source_id=source_id,
            eligibility=eligibility,
            barriers_identified=barriers_identified,
            recommended_actions=recommended_actions,
            difficulty=difficulty,
            estimated_earnings_potential=estimated_earnings,
            onboarding_time_minutes=onboarding_minutes,
            metadata={"platform": platform, "source_data": source_data},
        )

        self._assessment_cache[source_id] = assessment
        logger.info(f"[ELIGIBILITY] Source {source_id}: {eligibility.value} - barriers: {barriers_identified} - earnings: ${estimated_earnings:.2f}/day")

        return assessment

    def assess_opportunity(self, opportunity_id: str, opportunity_data: dict[str, Any]) -> EligibilityAssessment:
        """Assess an opportunity for zero-barrier eligibility.

        Args:
            opportunity_id: Unique identifier for the opportunity
            opportunity_data: Opportunity metadata including title, description, amount, barriers

        Returns:
            EligibilityAssessment with status and recommendations
        """
        barriers_identified: list[BarrierType] = []
        difficulty = opportunity_data.get("difficulty", "beginner")
        onboarding_minutes = 10
        estimated_earnings = opportunity_data.get("amount", 0.0)
        eligibility = EligibilityStatus.APPROVED
        recommended_actions: list[str] = []

        # Check barriers from opportunity data
        barriers_raw = opportunity_data.get("barriers", [])

        for barrier_raw in barriers_raw:
            try:
                barrier = BarrierType(barrier_raw)
                barriers_identified.append(barrier)

                if barrier == BarrierType.INTERVIEW:
                    eligibility = EligibilityStatus.INTERVIEW_REQUIRED
                    recommended_actions.append("Interview required; not zero-barrier")
                    onboarding_minutes = 60
                elif barrier == BarrierType.PORTFOLIO:
                    eligibility = EligibilityStatus.CONDITIONAL
                    recommended_actions.append("Portfolio required; conditional zero-barrier with portfolio submission")
                    onboarding_minutes = 30
                elif barrier in [BarrierType.EXPERIENCE, BarrierType.DEGREE, BarrierType.CERTIFICATION]:
                    eligibility = EligibilityStatus.EXPERIENCE_REQUIRED
                    recommended_actions.append(f"{barrier.value} required; not zero-barrier eligible")
                    onboarding_minutes = 60
                    estimated_earnings = 0.0  # Cannot estimate without meeting requirements
                else:
                    # Other barriers - conditional
                    if eligibility != EligibilityStatus.INTERVIEW_REQUIRED:
                        eligibility = EligibilityStatus.CONDITIONAL
            except ValueError:
                # Unknown barrier type
                pass

        # Check difficulty threshold
        if difficulty in ["advanced", "expert"] and self.criteria.max_difficulty == "beginner" and eligibility == EligibilityStatus.APPROVED:
            eligibility = EligibilityStatus.CONDITIONAL
            recommended_actions.append(f"Difficulty '{difficulty}' exceeds maximum '{self.criteria.max_difficulty}'")
            onboarding_minutes = 30
            # Reduce earnings estimate for high-difficulty beginner tasks
            with contextlib.suppress(TypeError, ValueError):
                estimated_earnings = min(estimated_earnings, 50.0)  # Cap at $50 for beginner-level high-difficulty

        # Check amount threshold (very low amounts may not be worth onboarding)
        amount = opportunity_data.get("amount", 0.0)
        if amount < 5.0 and eligibility == EligibilityStatus.APPROVED:
            eligibility = EligibilityStatus.CONDITIONAL
            recommended_actions.append("Very low reward; consider combining with other opportunities")

        assessment = EligibilityAssessment(
            source_id=opportunity_id,
            eligibility=eligibility,
            barriers_identified=barriers_identified,
            recommended_actions=recommended_actions,
            difficulty=difficulty,
            estimated_earnings_potential=float(estimated_earnings),
            onboarding_time_minutes=onboarding_minutes,
            metadata={
                "opportunity_title": opportunity_data.get("title", "Unknown"),
                "platform": opportunity_data.get("platform", "unknown"),
            },
        )

        logger.info(f"[ELIGIBILITY] Opportunity {opportunity_id}: {eligibility.value} - barriers: {barriers_identified} - earnings: ${estimated_earnings}")

        return assessment

    def _estimate_earnings(self, platform: str, source_data: dict[str, Any]) -> float:
        """Estimate daily earnings potential for a source.

        Args:
            platform: Platform name (bug_bounty, dev_bounty, data_annotation, etc.)
            source_data: Source metadata

        Returns:
            Estimated daily earnings in USD
        """
        # Base rates per platform (annualized, divided by 365 for daily)
        base_rates = {
            "bug_bounty": 500.0,  # avg per opportunity * success rate
            "dev_bounty": 150.0,
            "data_annotation": 10.0,
            "ai_training": 20.0,
            "survey": 5.0,
            "usertesting": 30.0,
        }

        base_rate = base_rates.get(platform, 10.0)

        # Adjust based on success rate if provided
        success_rate = source_data.get("success_rate", 0.0)
        if success_rate:
            base_rate *= success_rate

        # Adjust based on daily capacity
        daily_capacity = source_data.get("daily_capacity", 1)
        if daily_capacity:
            base_rate *= min(daily_capacity, 10) / 1.0  # Cap multiplier at 10x

        return round(base_rate, 2)

    def get_eligibility_summary(self) -> dict[str, Any]:
        """Get summary of eligibility criteria and statuses.

        Returns:
            Dictionary with eligibility system summary
        """
        return {
            "criteria": {
                "forbidden_barriers": [b.value for b in self.criteria.forbidden_barriers],
                "max_difficulty": self.criteria.max_difficulty,
                "acceptable_domains": self.criteria.acceptable_domains,
                "max_daily_hours": self.criteria.max_daily_hours,
                "min_success_rate": self.criteria.min_success_rate,
            },
            "eligibility_levels": {
                level.value: {
                    "description": self._get_eligibility_description(level),
                    "onboarding_minutes": self._get_onboarding_minutes(level),
                }
                for level in EligibilityStatus
            },
        }

    def _get_eligibility_description(self, status: EligibilityStatus) -> str:
        """Get human-readable description for eligibility status."""
        descriptions = {
            EligibilityStatus.APPROVED: "Zero-barrier: No interview, portfolio, or experience required. Direct access.",
            EligibilityStatus.CONDITIONAL: "Conditional: Minimal onboarding required (typically <30 minutes).",
            EligibilityStatus.EXPERIENCE_REQUIRED: "Experience required: Proven track record needed.",
            EligibilityStatus.INTERVIEW_REQUIRED: "Interview required: Formal selection process.",
            EligibilityStatus.DEGREE_REQUIRED: "Degree required: Formal qualification needed.",
        }
        return descriptions.get(status, "Unknown status")

    def _get_onboarding_minutes(self, status: EligibilityStatus) -> int:
        """Get typical onboarding time in minutes for eligibility status."""
        minutes = {
            EligibilityStatus.APPROVED: 5,
            EligibilityStatus.CONDITIONAL: 15,
            EligibilityStatus.EXPERIENCE_REQUIRED: 60,
            EligibilityStatus.INTERVIEW_REQUIRED: 60,
            EligibilityStatus.DEGREE_REQUIRED: 120,
        }
        return minutes.get(status, 30)


# Singleton instance for global access
_eligibility_engine: ZeroBarrierEligibilityEngine | None = None


def get_eligibility_engine() -> ZeroBarrierEligibilityEngine:
    """Get or create the global zero-barrier eligibility engine instance.

    Returns:
        Global ZeroBarrierEligibilityEngine instance
    """
    global _eligibility_engine
    if _eligibility_engine is None:
        _eligibility_engine = ZeroBarrierEligibilityEngine()
    return _eligibility_engine


def assess_source_zero_barrier(source_id: str, source_data: dict[str, Any]) -> EligibilityAssessment:
    """Convenience function to assess source zero-barrier eligibility.

    Args:
        source_id: Unique identifier for the source
        source_data: Source metadata

    Returns:
        EligibilityAssessment result
    """
    engine = get_eligibility_engine()
    return engine.assess_source(source_id, source_data)


def assess_opportunity_zero_barrier(opportunity_id: str, opportunity_data: dict[str, Any]) -> EligibilityAssessment:
    """Convenience function to assess opportunity zero-barrier eligibility.

    Args:
        opportunity_id: Unique identifier for the opportunity
        opportunity_data: Opportunity metadata

    Returns:
        EligibilityAssessment result
    """
    engine = get_eligibility_engine()
    return engine.assess_opportunity(opportunity_id, opportunity_data)


def assess_source_with_verification(self, source_id: str, user_residence: str = "Argentina") -> EligibilityAssessment:
    """Assess source eligibility with full verification chain.

    Evaluates source for zero-barrier access verifying residence.
    Does NOT auto-approve just because no professional barriers exist.
    Each source is verified individually for Argentina residency and payout viability.

    Args:
        source_id: Unique identifier for the source
        user_residence: User's residence country for geographical filtering

    Returns:
        EligibilityAssessment with status and verification reasons
    """
    from cores.source_intelligence.registry import SourceRegistry
    from cores.source_intelligence.verifier import SourceVerifier

    registry = SourceRegistry()
    verifier = SourceVerifier(registry, payment_engine=None, country=user_residence)

    # Step 1: Verify SOURCE exists in registry
    source_info = registry.get_source(source_id)
    if not source_info:
        return EligibilityAssessment(
            source_id=source_id,
            eligibility=EligibilityStatus.NOT_IMPLEMENTED,
            barriers_identified=[],
            recommended_actions=[f"Source '{source_id}' not found in registry"],
            difficulty="beginner",
            estimated_earnings_potential=0.0,
            onboarding_time_minutes=0,
            metadata={"verification_steps": ["source_not_found"]},
        )

    # Step 2: Run full verification pipeline (eligibility + integration + payout)
    verdict = verifier.verify_source(source_id)

    # Extract results from verdict
    elig_pass = verdict.eligibility.result == "pass"
    integ_pass = verdict.integration.result == "pass"
    payout_pass = verdict.payout.result == "pass"

    # Build assessment based on verification results
    if not (elig_pass and integ_pass and payout_pass):
        # ANY check fails - do NOT auto-approve
        barriers = []
        reasons = []
        if not elig_pass:
            barriers.append(BarrierType.EXPERIENCE)
            reasons.append(verdict.eligibility.detail or "Restricciones de elegibilidad")
        if not integ_pass:
            reasons.append(verdict.integration.detail or "No es posible integrar/ejecutar")
        if not payout_pass:
            reasons.append(verdict.payout.detail or "No hay ruta de retiro viable")

        eligibility = EligibilityStatus.EXPERIENCE_REQUIRED
        estimated_earnings = 0.0
        onboarding_minutes = 60
        recommended_actions = reasons + ["Verificar requisitos por plataforma, programa y método de pago"]
        metadata = {"verification_steps": [], "user_residence": user_residence, "partial_failures": reasons}
    else:
        # ALL CHECKS PASSED - full zero-barrier approval
        original_assessment = self.assess_source(source_id, {})
        eligibility = EligibilityStatus.APPROVED
        estimated_earnings = original_assessment.estimated_earnings_potential if original_assessment else 0.0
        onboarding_minutes = original_assessment.onboarding_time_minutes if original_assessment else 5
        recommended_actions = original_assessment.recommended_actions + [f"Full verification passed for residence: {user_residence}"]
        metadata = {
            "verification_steps": ["eligibility_passed", "integration_passed", "payout_passed"],
            "user_residence": user_residence,
            "source_info": {"name": source_info.name, "domains": source_info.domains},
        }

    assessment = EligibilityAssessment(
        source_id=source_id,
        eligibility=eligibility,
        barriers_identified=[],
        recommended_actions=recommended_actions,
        difficulty="beginner",
        estimated_earnings_potential=float(estimated_earnings),
        onboarding_time_minutes=onboarding_minutes,
        metadata=metadata,
    )

    logger.info(
        f"[ELIGIBILITY-FULL] Source {source_id}: {eligibility.value} "
        f"- residence: {user_residence} - checks: elig={elig_pass}, integ={integ_pass}, payout={payout_pass}"
    )

    return assessment
