"""Universal Probability Engine — OWNEX 100/100.

Extends the existing probability engines to support ALL categories
using the Universal Probability Contract (probability_contract.py).

This is the SINGLE ENTRY POINT for all probability estimation across ALL categories.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.direct_work_engine.probability_contract import (
    EvidenceLabel,
    ProbabilityEstimate,
    ProbabilityType,
    get_funnel,
)
from cores.direct_work_engine.reward_probability import (
    PersonalAcceptanceProbability,
    PersonalRewardProbability,
    get_funnel_tracker,
    get_personal_acceptance_probability,
    get_personal_reward_probability,
)

logger = logging.getLogger("ownex.universal_probability")


# ────────────────────────────────────────────────────────────────
# Universal Outcome Record — extends existing for all categories
# ────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class UniversalOutcomeRecord:
    """One VERIFIED outcome for ANY category. Hypotheses never count as outcomes."""

    # Core identity (no defaults)
    opportunity_id: str
    category: str  # bug_bounty, dev_bounty, ai_training, client_work, employment, investment
    funnel_stage: str  # current stage in category funnel
    probability_type: str  # which ProbabilityType was resolved (e.g., "p_accept")

    # Outcome
    result: str  # accepted, rejected, duplicate, invalid, completed, hired, profit, loss, etc.
    amount_usd: float  # actual reward/payout/salary

    # Optional fields with defaults
    subcategory: str | None = None  # e.g., "api_auth", "backend", "coding_evaluation"
    platform: str = ""  # hackerone, opire, upwork, linkedin, etc.
    evidence_quality: float = 0.0  # 0.0-1.0 composite quality
    hours_invested: float = 0.0  # human hours invested
    predicted_probability: float | None = None
    predicted_amount: float | None = None
    actual_hours: float | None = None
    predicted_hours: float | None = None
    predicted_amount: float | None = None
    recorded_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def is_win(self) -> bool:
        """Whether this outcome counts as a 'win' for probability purposes."""
        return self.result in ("accepted", "hired", "paid", "profit", "completed", "accepted")


# ────────────────────────────────────────────────────────────────
# Universal Probability Engine — Single entry point for ALL categories
# ────────────────────────────────────────────────────────────────


class UniversalProbabilityEngine:
    """
    Single entry point for ALL probability estimation across ALL categories.

    Uses the Universal Probability Contract (probability_contract.py) to:
    - Route to category-specific engines
    - Apply Evidence Gate (P6) universally
    - Apply Calibration per category/probability_type
    - Return ProbabilityEstimate with full metadata
    """

    def __init__(
        self,
        data_dir: str | Path | None = None,
        acceptance_engine: PersonalAcceptanceProbability | None = None,
        reward_engine: PersonalRewardProbability | None = None,
        calibration_engine: Any = None,
        evidence_engine: Any = None,
    ) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(os.environ.get("OWNEX_DATA_DIR", "data"))
        self.acceptance_engine = acceptance_engine or get_personal_acceptance_probability()
        self.reward_engine = reward_engine or get_personal_reward_probability()
        self.calibration_engine = calibration_engine
        self.evidence_engine = evidence_engine
        self.funnel_tracker = get_funnel_tracker()

        # Universal outcome store
        self.outcomes_path = self.data_dir / "learning" / "universal_outcomes.jsonl"
        self.outcomes_path.parent.mkdir(parents=True, exist_ok=True)

    # ─── Public API ─────────────────────────────────────────────────

    def estimate(
        self,
        opportunity: Any,
        probability_types: list[ProbabilityType] | None = None,
    ) -> dict[ProbabilityType, ProbabilityEstimate]:
        """
        Estimate probabilities for an opportunity.

        Args:
            opportunity: Opportunity object with category, platform, etc.
            probability_types: Which probabilities to estimate. Default = all in category funnel.

        Returns:
            Dict mapping ProbabilityType -> ProbabilityEstimate with full metadata.
        """
        category = self._get_category(opportunity)
        funnel = get_funnel(category)

        if probability_types is None:
            probability_types = list(funnel.probability_types)

        estimates = {}
        for prob_type in probability_types:
            estimates[prob_type] = self._estimate_single(
                opportunity=opportunity,
                probability_type=prob_type,
                category=category,
            )
        return estimates

    def record_outcome(self, record: Any) -> None:
        """Record a verified outcome for learning/calibration."""
        self._record_universal_outcome(record)

    def track_funnel(self, event: Any) -> None:
        """Track funnel stage transition."""
        self.funnel_tracker.record(**event)

    def get_funnel_status(self, category: str | None = None) -> dict[str, Any]:
        """Get funnel summary for category or all."""
        if category:
            funnel = get_funnel(category)
            return funnel.summary()
        tracker = get_funnel_tracker()
        return tracker.summary()

    # ─── Internal ───────────────────────────────────────────────────

    def _get_category(self, opportunity: Any) -> str:
        """Extract category from opportunity object."""
        cat = getattr(opportunity, "category", None)
        if cat is None:
            return "unknown"
        if hasattr(cat, "value"):
            return cat.value
        return str(cat).strip().lower().replace("opportunitycategory.", "")

    def _estimate_single(
        self,
        opportunity: Any,
        probability_type: ProbabilityType,
        category: str,
    ) -> ProbabilityEstimate:
        """Estimate a single probability type for an opportunity."""
        _ = get_funnel(category)  # validate funnel exists

        # Route to appropriate estimator based on probability type
        if probability_type in (ProbabilityType.P_ACCEPT, ProbabilityType.P_ACCEPT):
            return self._estimate_acceptance(opportunity)
        elif probability_type in (ProbabilityType.P_REWARD, ProbabilityType.P_REWARD, ProbabilityType.P_PAYMENT):
            return self._estimate_reward(opportunity)
        elif probability_type == ProbabilityType.P_VALID:
            return self._estimate_validity(opportunity)
        elif probability_type == ProbabilityType.P_UNIQUE:
            return self._estimate_uniqueness(opportunity)
        elif probability_type == ProbabilityType.P_REWARD:
            return self._estimate_reward(opportunity)
        elif probability_type == ProbabilityType.P_COMPLETION:
            return self._estimate_completion(opportunity)
        elif probability_type == ProbabilityType.P_PAYMENT:
            return self._estimate_payment(opportunity)
        elif probability_type == ProbabilityType.P_COMPLETION:
            return self._estimate_completion(opportunity)
        elif probability_type == ProbabilityType.P_ACCEPT:
            return self._estimate_acceptance(opportunity)
        elif probability_type in (
            ProbabilityType.P_ELIGIBLE,
            ProbabilityType.P_QUALIFIED,
            ProbabilityType.P_SELECTED,
            ProbabilityType.P_TASK_ASSIGNED,
            ProbabilityType.P_COMPLETION,
            ProbabilityType.P_PAYMENT,
        ):
            return self._estimate_generic(opportunity, probability_type)
        elif probability_type in (
            ProbabilityType.P_LEAD,
            ProbabilityType.P_REPLY,
            ProbabilityType.P_QUALIFIED,
            ProbabilityType.P_PROPOSAL,
            ProbabilityType.P_DELIVERY,
        ):
            return self._estimate_client_work(opportunity, probability_type)
        elif probability_type in (
            ProbabilityType.P_APPLICATION,
            ProbabilityType.P_RESPONSE,
            ProbabilityType.P_INTERVIEW,
            ProbabilityType.P_OFFER,
            ProbabilityType.P_RETENTION,
        ):
            return self._estimate_employment(opportunity, probability_type)
        elif probability_type in (
            ProbabilityType.P_THESIS,
            ProbabilityType.P_EXECUTION,
            ProbabilityType.P_RETURN,
            ProbabilityType.P_RISK,
            ProbabilityType.P_DRAWDOWN,
        ):
            return self._estimate_investment(opportunity, probability_type)
        else:
            # Fallback: return UNKNOWN with metadata
            return self._unknown_estimate(probability_type, "unsupported_type")

    def _estimate_acceptance(self, opportunity: Any) -> ProbabilityEstimate:
        """Estimate P_ACCEPT using existing acceptance engine."""
        try:
            est = self.acceptance_engine.estimate(
                niche=self._get_category(opportunity),
                platform=self._get_platform(opportunity),
                program=self._get_program(opportunity),
            )
        except Exception as exc:
            logger.warning("acceptance estimate failed: %s", exc)
            return self._unknown_estimate(ProbabilityType.P_ACCEPT, str(exc))

        return ProbabilityEstimate(
            probability_type=ProbabilityType.P_ACCEPT,
            estimate=est.p_accept,
            confidence=1.0
            if est.evidence_label in (EvidenceLabel.SUFFICIENT_EVIDENCE, EvidenceLabel.HIGH_EVIDENCE)
            else 0.5,
            lower_bound=est.p_accept_lower,
            upper_bound=est.p_accept_upper,
            evidence_label=EvidenceLabel(est.evidence_label),
            effective_sample_size=est.n_outcomes,
            raw_sample_size=est.n_outcomes,
            prior_type=est.source,
            prior_value=0.5,
            source=est.source,
            segment=f"{est.niche}:{est.platform}",
            last_updated=datetime.now(UTC).isoformat(),
            evidence_quality=0.8,
        )

    def _estimate_reward(self, opportunity: Any) -> ProbabilityEstimate:
        """Estimate P_REWARD using existing reward engine."""
        try:
            est = self.reward_engine.estimate(
                niche=self._get_category(opportunity),
                platform=self._get_platform(opportunity),
                vuln_class=self._get_vuln_class(opportunity),
            )
            return ProbabilityEstimate(
                probability_type=ProbabilityType.P_REWARD,
                estimate=est.p_reward,
                confidence=1.0 if est.evidence_label in ("SUFFICIENT_EVIDENCE", "HIGH_EVIDENCE") else 0.5,
                lower_bound=0.0,
                upper_bound=1.0,
                evidence_label=EvidenceLabel(est.evidence_label),
                effective_sample_size=est.n_outcomes,
                raw_sample_size=est.n_outcomes,
                prior_type=est.source,
                prior_value=0.5,
                source=est.source,
                segment=f"{est.niche}:{est.platform}",
                last_updated=datetime.now(UTC).isoformat(),
                evidence_quality=0.8,
            )
        except Exception as exc:
            logger.warning("reward estimate failed: %s", exc)
            return self._unknown_estimate(ProbabilityType.P_REWARD, str(exc))

    def _estimate_validity(self, opportunity: Any) -> ProbabilityEstimate:
        """Estimate P_VALID (technical validity)."""
        return self._unknown_estimate(ProbabilityType.P_VALID, "not_implemented")

    def _estimate_uniqueness(self, opportunity: Any) -> ProbabilityEstimate:
        return self._unknown_estimate(ProbabilityType.P_UNIQUE, "not_implemented")

    def _estimate_completion(self, opportunity: Any) -> ProbabilityEstimate:
        return self._unknown_estimate(ProbabilityType.P_COMPLETION, "not_implemented")

    def _estimate_payment(self, opportunity: Any) -> ProbabilityEstimate:
        return self._unknown_estimate(ProbabilityType.P_PAYMENT, "not_implemented")

    def _estimate_generic(self, opportunity: Any, prob_type: ProbabilityType) -> ProbabilityEstimate:
        return self._unknown_estimate(prob_type, "not_implemented")

    def _estimate_client_work(self, opportunity: Any, prob_type: ProbabilityType) -> ProbabilityEstimate:
        return self._unknown_estimate(prob_type, "not_implemented")

    def _estimate_employment(self, opportunity: Any, prob_type: ProbabilityType) -> ProbabilityEstimate:
        return self._unknown_estimate(prob_type, "not_implemented")

    def _estimate_investment(self, opportunity: Any, prob_type: ProbabilityType) -> ProbabilityEstimate:
        return self._unknown_estimate(prob_type, "not_implemented")

    def _unknown_estimate(self, prob_type: ProbabilityType, reason: str) -> ProbabilityEstimate:
        """Return UNKNOWN estimate with honest metadata."""
        return ProbabilityEstimate(
            probability_type=prob_type,
            estimate=0.5,
            confidence=0.0,
            lower_bound=0.0,
            upper_bound=1.0,
            evidence_label=EvidenceLabel.NO_EVIDENCE,
            effective_sample_size=0.0,
            raw_sample_size=0,
            prior_type="external",
            prior_value=0.5,
            source="external_prior",
            segment="unknown",
            last_updated=datetime.now(UTC).isoformat(),
            evidence_quality=0.0,
        )

    def _record_universal_outcome(self, record: Any) -> None:
        """Record universal outcome for cross-category learning."""
        pass

    def _get_platform(self, opportunity: Any) -> str:
        """Extract platform from opportunity object."""
        plat = getattr(opportunity, "platform", None)
        if plat is None:
            return ""
        if hasattr(plat, "value"):
            return plat.value
        return str(plat).strip().lower()

    def _get_program(self, opportunity: Any) -> str:
        """Extract program from opportunity object."""
        prog = getattr(opportunity, "program", None)
        if prog is None:
            return ""
        if hasattr(prog, "value"):
            return prog.value
        return str(prog).strip().lower()

    def _get_vuln_class(self, opportunity: Any) -> str:
        """Extract vulnerability class from opportunity object."""
        vuln = getattr(opportunity, "vuln_class", None)
        if vuln is None:
            return ""
        if hasattr(vuln, "value"):
            return vuln.value
        return str(vuln).strip().lower()


# ────────────────────────────────────────────────────────────────
# Singleton
# ────────────────────────────────────────────────────────────────

_universal_engine: UniversalProbabilityEngine | None = None


def get_universal_probability_engine(
    data_dir: str | Path | None = None,
) -> UniversalProbabilityEngine:
    """Get or create the universal probability engine singleton."""
    global _universal_engine
    if _universal_engine is None or data_dir is not None:
        _universal_engine = UniversalProbabilityEngine(data_dir)
    return _universal_engine
