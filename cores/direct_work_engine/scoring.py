"""Zero Barrier Scorer — computes continuous 0-100 entry barrier scores for opportunities."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cores.direct_work_engine.models import (
    PAYMENT_RELIABILITY,
    BarrierLevel,
    ExperienceLevel,
    Opportunity,
    ZeroBarrierScore,
)

logger = logging.getLogger("ownex.direct_work_engine.scoring")


@dataclass(slots=True)
class ScorerWeights:
    """Weights for each barrier factor. Sum should be 1.0."""

    no_experience_required: float = 0.10
    no_portfolio_required: float = 0.08
    no_interview_required: float = 0.10
    direct_application: float = 0.06
    international_payment: float = 0.10
    payment_verified: float = 0.08
    remote_work: float = 0.08
    argentina_accessible: float = 0.08
    beginner_friendly: float = 0.06
    freelancer_friendly: float = 0.04
    individual_friendly: float = 0.04
    ai_tools_accepted: float = 0.04
    async_work_accepted: float = 0.04
    fast_payment: float = 0.06
    stable_income: float = 0.04

    def validate(self) -> bool:
        total = (
            self.no_experience_required
            + self.no_portfolio_required
            + self.no_interview_required
            + self.direct_application
            + self.international_payment
            + self.payment_verified
            + self.remote_work
            + self.argentina_accessible
            + self.beginner_friendly
            + self.freelancer_friendly
            + self.individual_friendly
            + self.ai_tools_accepted
            + self.async_work_accepted
            + self.fast_payment
            + self.stable_income
        )
        return abs(total - 1.0) < 0.001


DEFAULT_WEIGHTS = ScorerWeights()


class ZeroBarrierScorer:
    """Computes Zero Barrier Score for opportunities.

    Higher score = lower barrier to entry.
    Never promises zero barrier exists universally — only ranks opportunities.
    """

    def __init__(self, weights: ScorerWeights | None = None):
        self.weights = weights or DEFAULT_WEIGHTS
        self._normalize_weights()

    def _normalize_weights(self) -> None:
        """Normalize weights to sum to 1.0 so tuning one factor never breaks scoring."""
        import dataclasses

        names = [f.name for f in dataclasses.fields(self.weights)]
        total = sum(getattr(self.weights, name) for name in names)
        if abs(total - 1.0) < 1e-9:
            return
        for name in names:
            setattr(self.weights, name, getattr(self.weights, name) / total)

    def score(self, opportunity: Opportunity) -> ZeroBarrierScore:
        """Calculate zero barrier score for an opportunity."""
        factors: dict[str, float] = {}
        weights = self.weights

        # 1. No experience required
        factors["no_experience_required"] = self._score_experience(opportunity)

        # 2. No portfolio required
        factors["no_portfolio_required"] = self._score_portfolio(opportunity)

        # 3. No interview required
        factors["no_interview_required"] = self._score_interview(opportunity)

        # 4. Direct application (no complex forms)
        factors["direct_application"] = self._score_direct_application(opportunity)

        # 5. International payment
        factors["international_payment"] = self._score_international_payment(opportunity)

        # 6. Payment verified/proven
        factors["payment_verified"] = self._score_payment_verified(opportunity)

        # 7. Remote work
        factors["remote_work"] = self._score_remote_work(opportunity)

        # 8. Argentina accessible
        factors["argentina_accessible"] = self._score_argentina_accessible(opportunity)

        # 9. Beginner friendly
        factors["beginner_friendly"] = self._score_beginner_friendly(opportunity)

        # 10. Freelancer friendly
        factors["freelancer_friendly"] = self._score_freelancer_friendly(opportunity)

        # 11. Individual friendly
        factors["individual_friendly"] = self._score_individual_friendly(opportunity)

        # 12. AI tools accepted
        factors["ai_tools_accepted"] = self._score_ai_tools(opportunity)

        # 13. Async work accepted
        factors["async_work_accepted"] = self._score_async_work(opportunity)

        # 14. Fast payment
        factors["fast_payment"] = self._score_fast_payment(opportunity)

        # 15. Stable income
        factors["stable_income"] = self._score_stable_income(opportunity)

        # Calculate weighted total
        total = sum(factors[k] * getattr(weights, k) for k in factors)

        # Determine barrier level
        barrier_level = self._determine_barrier_level(total)

        # Build reasoning
        reasoning, blockers, enablers = self._build_reasoning(opportunity, factors)

        return ZeroBarrierScore(
            total=round(total, 1),
            factors={k: round(v, 1) for k, v in factors.items()},
            weights=self._weights_dict(),
            barrier_level=barrier_level,
            reasoning=reasoning,
            enablers=enablers,
            blockers=blockers,
        )

    def _weights_dict(self) -> dict[str, float]:
        """Export weights as a plain dict (works with slots dataclass)."""
        import dataclasses

        return {f.name: getattr(self.weights, f.name) for f in dataclasses.fields(self.weights)}

    def score_opportunities(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        """Score multiple opportunities in place; return sorted by score descending."""
        for opp in opportunities:
            opp.zero_barrier_score = self.score(opp)
        return sorted(
            opportunities,
            key=lambda o: o.zero_barrier_score.total if o.zero_barrier_score else 0.0,
            reverse=True,
        )

    def _score_experience(self, opp: Opportunity) -> float:
        """Score based on experience requirements."""
        if opp.experience_required == ExperienceLevel.NONE:
            return 100.0
        elif opp.experience_required == ExperienceLevel.JUNIOR:
            return 70.0
        elif opp.experience_required == ExperienceLevel.MID:
            return 40.0
        else:  # SENIOR
            return 10.0

    def _score_portfolio(self, opp: Opportunity) -> float:
        """Score based on portfolio requirements."""
        if not opp.portfolio_required:
            return 100.0
        # Portfolio optional but preferred
        return 30.0

    def _score_interview(self, opp: Opportunity) -> float:
        """Score based on interview requirements."""
        if not opp.interview_required:
            return 100.0
        # Has interview - check stages (1=low barrier, many=high)
        return max(0.0, 100.0 - 25.0)  # one interview = 75, more = lower

    def _score_direct_application(self, opp: Opportunity) -> float:
        """Score based on application complexity.

        A one-time capability assessment (technical test) is NOT a hiring
        funnel: it amortizes over the whole work stream and proves skill
        rather than gating on identity/history. It costs some friction
        (still below a plain registration form), but never the crushing
        penalty the old model applied.
        """
        if not opp.registration_required:
            if opp.technical_test_required:
                return 70.0  # assessment-only entry: amortizable, not a funnel
            return 100.0
        # Registration required
        if opp.technical_test_required:
            return 50.0  # registration + one-time assessment
        return 60.0

    def _score_international_payment(self, opp: Opportunity) -> float:
        """Score based on international payment capability."""
        if opp.international_payment:
            return 100.0
        # Check payment method
        reliability = PAYMENT_RELIABILITY.get(opp.payment_method, 0.5)
        return reliability * 100.0

    def _score_payment_verified(self, opp: Opportunity) -> float:
        """Score based on payment verification."""
        if opp.payment_proven:
            return 100.0
        # Platform reputation as proxy
        return opp.reputation * 100.0

    def _score_remote_work(self, opp: Opportunity) -> float:
        """Score based on remote work policy."""
        if opp.remote:
            return 100.0
        return 0.0

    def _score_argentina_accessible(self, opp: Opportunity) -> float:
        """Score based on Argentina accessibility."""
        # Platform-level checks would go here
        # For now, use remote + international payment as proxy
        if opp.remote and opp.international_payment:
            return 90.0
        elif opp.remote:
            return 60.0
        return 10.0

    def _score_beginner_friendly(self, opp: Opportunity) -> float:
        """Score based on beginner friendliness."""
        if opp.accepts_beginner:
            return 100.0
        return 0.0

    def _score_freelancer_friendly(self, opp: Opportunity) -> float:
        """Score based on freelancer friendliness."""
        if opp.accepts_freelancers:
            return 100.0
        return 0.0

    def _score_individual_friendly(self, opp: Opportunity) -> float:
        """Score based on individual (non-corp) friendliness."""
        if opp.accepts_individuals:
            return 100.0
        return 0.0

    def _score_ai_tools(self, opp: Opportunity) -> float:
        """Score based on AI tool acceptance."""
        if opp.accepts_ai_tools:
            return 100.0
        return 50.0  # Neutral if unknown

    def _score_async_work(self, opp: Opportunity) -> float:
        """Score based on async work acceptance."""
        if opp.asynchronous:
            return 100.0
        return 40.0

    def _score_fast_payment(self, opp: Opportunity) -> float:
        """Score based on time to first payment."""
        if opp.time_to_payout_days is None:
            return 50.0  # Unknown
        if opp.time_to_payout_days <= 7:
            return 100.0
        elif opp.time_to_payout_days <= 14:
            return 80.0
        elif opp.time_to_payout_days <= 30:
            return 60.0
        elif opp.time_to_payout_days <= 60:
            return 30.0
        else:
            return 10.0

    def _score_stable_income(self, opp: Opportunity) -> float:
        """Score based on income stability."""
        # Combine reputation, stability, and risk
        stability_score = (opp.stability + opp.reputation + (1.0 - opp.risk)) / 3.0
        return stability_score * 100.0

    def _determine_barrier_level(self, total: float) -> BarrierLevel:
        """Map total score to barrier level."""
        if total >= 95:
            return BarrierLevel.ZERO
        elif total >= 80:
            return BarrierLevel.VERY_LOW
        elif total >= 60:
            return BarrierLevel.LOW
        elif total >= 40:
            return BarrierLevel.MEDIUM
        else:
            return BarrierLevel.HIGH

    def _build_reasoning(self, opp: Opportunity, factors: dict[str, float]) -> tuple[list[str], list[str], list[str]]:
        """Build human-readable reasoning, blockers, and enablers."""
        reasoning: list[str] = []
        blockers: list[str] = []
        enablers: list[str] = []

        # Check each factor
        if factors["no_experience_required"] >= 80:
            enablers.append("No experience required")
        elif factors["no_experience_required"] < 50:
            blockers.append(f"Requires {opp.experience_required.value}+ experience")

        if factors["no_portfolio_required"] >= 80:
            enablers.append("No portfolio required")
        elif opp.portfolio_required:
            blockers.append("Portfolio required")

        if factors["no_interview_required"] >= 80:
            enablers.append("No interview required")
        elif opp.interview_required:
            blockers.append("Interview required")

        if opp.technical_test_required:
            if opp.experience_required == ExperienceLevel.NONE:
                enablers.append("Capability assessment only (one-time; no prior experience needed)")
            else:
                blockers.append("Technical test required")

        if factors["international_payment"] >= 80:
            enablers.append("International payment supported")
        elif not opp.international_payment:
            blockers.append("No international payment method")

        if factors["payment_verified"] >= 80:
            enablers.append("Payment history verified")
        elif not opp.payment_proven:
            blockers.append("Payment not verified")

        if factors["remote_work"] >= 80:
            enablers.append("Fully remote")
        elif not opp.remote:
            blockers.append("Not remote")

        if factors["fast_payment"] >= 80:
            enablers.append("Fast payment (≤7 days)")
        elif opp.time_to_payout_days and opp.time_to_payout_days > 30:
            blockers.append(f"Slow payment ({int(opp.time_to_payout_days)} days)")

        if factors["beginner_friendly"] >= 80:
            enablers.append("Beginner friendly")
        elif not opp.accepts_beginner:
            blockers.append("Not beginner friendly")

        if factors["freelancer_friendly"] >= 80:
            enablers.append("Freelancer friendly")
        elif not opp.accepts_freelancers:
            blockers.append("Not freelancer friendly")

        if factors["ai_tools_accepted"] >= 80:
            enablers.append("AI tools accepted")

        if factors["async_work_accepted"] >= 80:
            enablers.append("Async work accepted")

        # Overall reasoning
        reasoning.append(f"Zero Barrier Score: {sum(factors[k] * getattr(self.weights, k) for k in factors):.1f}/100")
        reasoning.append(
            f"Barrier Level: {self._determine_barrier_level(sum(factors[k] * getattr(self.weights, k) for k in factors)).value}"
        )

        if blockers:
            reasoning.append("Blockers: " + "; ".join(blockers))
        if enablers:
            reasoning.append("Enablers: " + "; ".join(enablers))

        return reasoning, blockers, enablers


def score_opportunity(opportunity: Opportunity) -> ZeroBarrierScore:
    """Convenience function to score a single opportunity."""
    scorer = ZeroBarrierScorer()
    return scorer.score(opportunity)


def score_opportunities(opportunities: list[Opportunity]) -> list[Opportunity]:
    """Score multiple opportunities in place and return sorted by score (highest first)."""
    scorer = ZeroBarrierScorer()
    for opp in opportunities:
        opp.zero_barrier_score = scorer.score(opp)
    return sorted(opportunities, key=lambda o: o.zero_barrier_score.total if o.zero_barrier_score else 0, reverse=True)


# ── BarrierProfile — explicación factor-por-factor (Fase B, spec §7) ──

_BARRIER_FACTOR_LABELS: tuple[tuple[str, str], ...] = (
    ("interview_required", "entrevista"),
    ("portfolio_required", "portfolio"),
    ("experience_required", "experiencia previa"),
    ("technical_test_required", "prueba técnica"),
    ("registration_required", "registro"),
)


def barrier_profile(opportunity) -> dict:
    """Factor-by-factor barrier checklist + plain-language explanation.

    Contract (spec §7): 'Zero Barrier' must be EXPLAINED, never just a
    score. Only verified boolean fields on the opportunity are consulted;
    fields the model does not carry (capital, approval) are reported as
    assumptions rather than asserted-false.
    """
    # experience_required es un enum (ExperienceLevel): solo bloquea si
    # exige algo distinto de NONE (bool("none") es truthy — trampa clásica).
    exp = getattr(opportunity, "experience_required", None)
    exp_value = str(getattr(exp, "value", exp) or "").strip().lower()
    factors = {
        label: (
            exp_value not in ("", "none") if attr == "experience_required" else bool(getattr(opportunity, attr, False))
        )
        for attr, label in _BARRIER_FACTOR_LABELS
    }
    remote = bool(getattr(opportunity, "remote", True))
    international = bool(getattr(opportunity, "international_payment", True))
    geo_restricted = not (remote and international)
    factors["restricción geográfica"] = geo_restricted

    # Registro gratuito es fricción menor, NO bloqueante del concepto
    # zero-barrier (Outlier exige cuenta y sigue siendo entrada libre).
    blocking = sorted(label for attr, label in _BARRIER_FACTOR_LABELS if label != "registro" and factors[label])

    if not blocking and not geo_restricted:
        note = " Requiere registro gratuito." if factors.get("registro") else ""
        explanation = (
            "Zero Barrier: sin entrevista, portfolio, experiencia previa, "
            "prueba técnica ni restricción geográfica para Argentina." + note
        )
        candidate = True
    else:
        detail = ", ".join(blocking) if blocking else "restricción geográfica"
        explanation = f"Barreras detectadas: requiere/implica {detail}."
        candidate = False

    return {
        "factors": factors,
        "blocking": blocking,
        "geo_restricted": geo_restricted,
        "is_zero_barrier_candidate": candidate,
        "explanation": explanation,
    }
