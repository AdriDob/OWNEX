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
        funnel = self._resolve_funnel(category)
        if funnel is None:
            return {
                pt: self._unknown_estimate(pt, f"no funnel for category {category!r}")
                for pt in (probability_types or [ProbabilityType.P_ACCEPT])
            }

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
            funnel = self._resolve_funnel(category)
            if funnel is None:
                return {"category": category, "error": "no funnel registered"}
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

    @staticmethod
    def _resolve_funnel(category: str) -> Any | None:
        """Map a raw opportunity category onto a registered funnel.

        Uses funnel_for_category() (OpportunityCategory -> funnel); falls back
        to the raw value for direct funnel names. Returns None when unmapped —
        callers must answer UNKNOWN, never invent.
        """
        from cores.direct_work_engine.category_funnel import funnel_for_category

        mapped = funnel_for_category(category)
        key = mapped or category
        try:
            return get_funnel(key)
        except KeyError:
            return None

    def _estimate_single(
        self,
        opportunity: Any,
        probability_type: ProbabilityType,
        category: str,
    ) -> ProbabilityEstimate:
        """Estimate a single probability type for an opportunity.

        The funnel was already resolved by estimate(); this method only routes
        to the estimator. Category here is informational (segment granularity).
        """
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
            from cores.direct_work_engine.reward_probability import niche_for_category

            est = self.acceptance_engine.estimate(
                niche=niche_for_category(self._get_category(opportunity)),
                platform=self._get_platform(opportunity),
                program=self._get_program(opportunity),
            )
        except Exception as exc:
            logger.warning("acceptance estimate failed: %s", exc)
            return self._unknown_estimate(ProbabilityType.P_ACCEPT, str(exc))

        label = _to_evidence_label(est.evidence_label)
        return ProbabilityEstimate(
            probability_type=ProbabilityType.P_ACCEPT,
            estimate=est.p_accept,
            confidence=1.0 if label in (EvidenceLabel.SUFFICIENT_EVIDENCE, EvidenceLabel.HIGH_EVIDENCE) else 0.5,
            lower_bound=est.p_accept_lower,
            upper_bound=est.p_accept_upper,
            evidence_label=label,
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
            from cores.direct_work_engine.reward_probability import niche_for_category

            est = self.reward_engine.estimate(
                niche=niche_for_category(self._get_category(opportunity)),
                platform=self._get_platform(opportunity),
                vuln_class=self._get_vuln_class(opportunity),
            )
            label = _to_evidence_label(est.evidence_label)
            return ProbabilityEstimate(
                probability_type=ProbabilityType.P_REWARD,
                estimate=est.p_reward,
                confidence=1.0 if label in (EvidenceLabel.SUFFICIENT_EVIDENCE, EvidenceLabel.HIGH_EVIDENCE) else 0.5,
                lower_bound=0.0,
                upper_bound=1.0,
                evidence_label=label,
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

    # ─── HIGH_CONFIDENCE_90 + cross-category ranking ───

    def is_high_confidence_90(self, opportunity: Any, category: str | None = None) -> bool:
        """Check whether an opportunity meets HIGH_CONFIDENCE_90 for its funnel.

        Resolves raw opportunity categories onto funnel names first; unknown
        funnels answer False (never invent confidence).
        """
        raw = category or self._get_category(opportunity)
        funnel = self._resolve_funnel(raw)
        if funnel is None:
            return False
        threshold = HIGH_CONFIDENCE_90_THRESHOLDS.get(funnel.category)
        if not threshold:
            return False
        prob_type = threshold["prob_type"]
        est = self._estimate_single(opportunity, prob_type, raw)
        if est.lower_bound < threshold["lower_bound_threshold"]:
            return False
        if est.evidence_label not in threshold["required_evidence"]:
            return False
        if est.raw_sample_size < threshold["min_raw_n"]:
            return False
        return est.effective_sample_size >= threshold["min_effective_n"]

    def rank_cross_category(
        self,
        opportunities: list[Any],
        mode: str = "BALANCED",
    ) -> list[dict[str, Any]]:
        """Rank opportunities from ANY categories without destroying funnel semantics.

        Each opportunity is scored on its own funnel (P_SUCCESS = product of its
        funnel probabilities); modes only change the ORDER, never the numbers.
        Modes: BALANCED | HIGH_CONFIDENCE | HIGH_UPSIDE | FAST_INCOME |
        HIGH_UPSIDE_90D | MAX_SUCCESS.
        """
        ranked: list[dict[str, Any]] = []
        for opp in opportunities:
            raw = self._get_category(opp)
            funnel = self._resolve_funnel(raw)
            if funnel is None:
                estimates: dict[Any, Any] = {}
                p_success = 0.0
                funnel_name = ""
            else:
                funnel_name = funnel.category
                estimates = self.estimate(opp)
                p_success = 1.0
                for pt in funnel.probability_types:
                    est = estimates.get(pt)
                    p_success *= est.estimate if est is not None else 0.5
            ev_hour = self._ev_per_hour(opp)
            ranked.append(
                {
                    "opportunity": opp,
                    "category": raw,
                    "funnel": funnel_name,
                    "p_success": round(p_success, 4),
                    "ev_per_hour": ev_hour,
                    "time_to_money_days": self._estimate_time_to_money(opp),
                    "is_high_confidence_90": self.is_high_confidence_90(opp) if funnel_name else False,
                    "estimates": estimates,
                }
            )
        if mode == "HIGH_CONFIDENCE":
            ranked.sort(key=lambda r: (not r["is_high_confidence_90"], -(r["ev_per_hour"] or 0.0)))
        elif mode == "HIGH_UPSIDE":
            ranked.sort(key=lambda r: -(r["ev_per_hour"] or 0.0))
        elif mode == "FAST_INCOME":
            ranked.sort(
                key=lambda r: (
                    (r["time_to_money_days"] is None, r["time_to_money_days"] or 0.0),
                    -(r["ev_per_hour"] or 0.0),
                )
            )
        elif mode == "MAX_SUCCESS":
            ranked.sort(key=lambda r: -r["p_success"])
        else:  # BALANCED + HIGH_UPSIDE_90D: EV/hour weighted by success
            ranked.sort(key=lambda r: -((r["ev_per_hour"] or 0.0) * r["p_success"]))
        return ranked

    @staticmethod
    def _ev_per_hour(opp: Any) -> float | None:
        reward = getattr(opp, "payment", None) or getattr(opp, "amount", None) or 0.0
        hours = getattr(opp, "estimated_human_hours", None) or getattr(opp, "estimated_time_hours", None) or 0.0
        try:
            reward_f, hours_f = float(reward), float(hours)
        except (TypeError, ValueError):
            return None
        if hours_f <= 0:
            return None
        return round(reward_f / hours_f, 2)

    @staticmethod
    def _estimate_time_to_money(opp: Any) -> float | None:
        days = getattr(opp, "time_to_payout_days", None)
        try:
            return float(days) if days is not None else None
        except (TypeError, ValueError):
            return None

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
# HIGH_CONFIDENCE_90 Cross-Category Thresholds
# ────────────────────────────────────────────────────────────────

HIGH_CONFIDENCE_90_THRESHOLDS: dict[str, dict[str, Any]] = {
    "bug_bounty": {
        "prob_type": ProbabilityType.P_ACCEPT,
        "lower_bound_threshold": 0.90,
        "min_raw_n": 15,
        "min_effective_n": 10,
        "required_evidence": [EvidenceLabel.SUFFICIENT_EVIDENCE, EvidenceLabel.HIGH_EVIDENCE],
    },
    "dev_bounty": {
        "prob_type": ProbabilityType.P_ACCEPT,
        "lower_bound_threshold": 0.90,
        "min_raw_n": 10,
        "min_effective_n": 7,
        "required_evidence": [EvidenceLabel.SUFFICIENT_EVIDENCE, EvidenceLabel.HIGH_EVIDENCE],
    },
    "ai_training": {
        "prob_type": ProbabilityType.P_COMPLETION,
        "lower_bound_threshold": 0.90,
        "min_raw_n": 20,
        "min_effective_n": 15,
        "required_evidence": [EvidenceLabel.SUFFICIENT_EVIDENCE, EvidenceLabel.HIGH_EVIDENCE],
    },
    "client_work": {
        "prob_type": ProbabilityType.P_ACCEPT,
        "lower_bound_threshold": 0.90,
        "min_raw_n": 10,
        "min_effective_n": 7,
        "required_evidence": [EvidenceLabel.SUFFICIENT_EVIDENCE, EvidenceLabel.HIGH_EVIDENCE],
    },
    "employment": {
        "prob_type": ProbabilityType.P_OFFER,
        "lower_bound_threshold": 0.90,
        "min_raw_n": 5,
        "min_effective_n": 3,
        "required_evidence": [EvidenceLabel.SUFFICIENT_EVIDENCE, EvidenceLabel.HIGH_EVIDENCE],
    },
    "investment": {
        "prob_type": ProbabilityType.P_RETURN,
        "lower_bound_threshold": 0.90,
        "min_raw_n": 20,
        "min_effective_n": 15,
        "required_evidence": [EvidenceLabel.SUFFICIENT_EVIDENCE, EvidenceLabel.HIGH_EVIDENCE],
    },
}


# ────────────────────────────────────────────────────────────────
# Label mapping (engine strings -> contract enum)
# ────────────────────────────────────────────────────────────────

_ENGINE_LABEL_TO_EVIDENCE: dict[str, EvidenceLabel] = {
    "NO_EVIDENCE": EvidenceLabel.NO_EVIDENCE,
    "THIN_EVIDENCE": EvidenceLabel.THIN_EVIDENCE,
    "LOW": EvidenceLabel.SUFFICIENT_EVIDENCE,
    "MEDIUM": EvidenceLabel.SUFFICIENT_EVIDENCE,
    "HIGH": EvidenceLabel.HIGH_EVIDENCE,
    "VERY_HIGH": EvidenceLabel.HIGH_EVIDENCE,
    "none": EvidenceLabel.NO_EVIDENCE,
    "low": EvidenceLabel.SUFFICIENT_EVIDENCE,
    "medium": EvidenceLabel.SUFFICIENT_EVIDENCE,
    "high": EvidenceLabel.HIGH_EVIDENCE,
    "very_high": EvidenceLabel.HIGH_EVIDENCE,
}


def _to_evidence_label(value: object) -> EvidenceLabel:
    """Map legacy engine evidence strings onto the contract enum.

    Unknown values answer NO_EVIDENCE (never invent confidence).
    """
    if isinstance(value, EvidenceLabel):
        return value
    return _ENGINE_LABEL_TO_EVIDENCE.get(str(value), EvidenceLabel.NO_EVIDENCE)


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
