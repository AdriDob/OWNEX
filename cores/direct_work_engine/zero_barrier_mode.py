"""Zero-Barrier Mode — Explicit filter for opportunities requiring NO barriers.

Implements the "Zero Experience ≠ Zero Barrier" principle:
- Zero Experience: No formal work history needed (assessment = capability proof)
- Zero Barrier: Nothing between you and paid work (instant start, no gate)

This mode filters to ONLY opportunities where:
- No interview
- No portfolio required
- No technical test
- No registration gate
- International payment available
- Remote
- Work available immediately
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cores.direct_work_engine.scoring import ZeroBarrierScorer
from cores.payment_compat.engine import PaymentCompatibilityEngine

logger = logging.getLogger("ownex.zero_barrier_mode")


class ZeroBarrierTier(StrEnum):
    """Strictness tiers for zero-barrier filtering."""

    ABSOLUTE = "absolute"  # NO gates at all
    NEAR_ZERO = "near_zero"  # Only trivial gates (email signup)
    LOW = "low"  # Minor gates (quick signup, email verify)
    FILTERED = "filtered"  # Scored ≥ 95 on ZeroBarrierScore


@dataclass(slots=True)
class ZeroBarrierConfig:
    """Configuration for zero-barrier filtering."""

    tier: str = "absolute"
    min_score: int = 95
    require_international_payment: bool = True
    require_remote: bool = True
    allow_assessment_gate: bool = False  # if False, ANY assessment = reject


@dataclass(slots=True)
class ZeroBarrierResult:
    """Result of zero-barrier evaluation."""

    opportunity_id: str
    is_zero_barrier: bool
    tier: str
    score: int
    blockers: list[str]
    enablers: list[str]
    reasoning: str
    estimated_start_time_hours: float | None = None
    can_start_now: bool = False


class ZeroBarrierEngine:
    """Strict zero-barrier filter for opportunities."""

    def __init__(self, config: ZeroBarrierConfig | None = None) -> None:
        self.config = config or ZeroBarrierConfig()
        self._scorer = ZeroBarrierScorer()
        self._payment_engine = PaymentCompatibilityEngine()

    def evaluate(self, opportunity: Any, profile: Any = None) -> ZeroBarrierResult:
        """Evaluate a single opportunity against zero-barrier criteria."""
        opp = opportunity
        opp.platform.value if hasattr(opp.platform, "value") else str(opp.platform)

        blockers = []
        enablers = []

        # 1. Barrier gates (HARD blockers for ABSOLUTE tier)
        if getattr(opportunity, "interview_required", False):
            blockers.append("Entrevista requerida")
        if getattr(opportunity, "portfolio_required", False):
            blockers.append("Portfolio requerido")
        if getattr(opportunity, "technical_test_required", False):
            blockers.append("Prueba técnica requerida")
        if getattr(opportunity, "registration_required", False):
            blockers.append("Registro complejo requerido")

        # 2. Experience requirement
        exp_req = getattr(opportunity, "experience_requirement", None)
        if exp_req and exp_req != "NONE":
            blockers.append(f"Experiencia requerida: {exp_req}")

        # 3. Payment compatibility
        try:
            from cores.payment_compat.engine import PaymentRequirement

            PaymentRequirement(
                method=opportunity.payment_method.value
                if hasattr(opportunity.payment_method, "value")
                else str(opportunity.payment_method),
                currency=opportunity.currency,
                region="AR",
                amount=opportunity.payment,
                platform=opportunity.platform.value
                if hasattr(opportunity.platform, "value")
                else str(opportunity.platform),
            )
            # Would need to evaluate - for now use a simple check
            payment_ok = True  # placeholder
        except Exception:
            payment_ok = False

        if not payment_ok:
            blockers.append("Método de pago no compatible con Argentina")

        # 3. International payment
        if getattr(opportunity, "international_payment", False) is False:
            blockers.append("No acepta pagos internacionales")

        # 4. Remote requirement
        if not getattr(opportunity, "remote", True):
            blockers.append("No es remoto")

        # 5. Zero Barrier Score
        score_obj = getattr(opportunity, "zero_barrier_score", None)
        score = score_obj.overall if score_obj else 0

        # Determine if zero-barrier
        is_zero = len(blockers) == 0

        # Assign tier
        if is_zero and score >= 95:
            tier = "absolute"
        elif len(blockers) == 0 and score >= 90:
            tier = "near_zero"
        elif score >= 80:
            tier = "low"
        elif score >= 60:
            tier = "filtered"
        else:
            tier = "filtered"

        # Enablers (positive signals)
        if not getattr(opportunity, "interview_required", False):
            enablers.append("Sin entrevista")
        if not getattr(opportunity, "portfolio_required", False):
            enablers.append("Sin portfolio")
        if not getattr(opportunity, "technical_test_required", False):
            enablers.append("Sin prueba técnica")
        if getattr(opportunity, "remote", True):
            enablers.append("100% remoto")
        if getattr(opportunity, "international_payment", False):
            enablers.append("Pago internacional OK")

        # Estimated start time
        est_start = None
        if score >= 95 and len(blockers) == 0:
            est_start = 0.5  # Can start in ~30 min
        elif score >= 90:
            est_start = 2.0  # Can start in ~2 hours
        elif score >= 80:
            est_start = 8.0  # Same day

        can_start = len(blockers) == 0 and score >= 80

        return ZeroBarrierResult(
            opportunity_id=getattr(opportunity, "id", "unknown"),
            is_zero_barrier=is_zero,
            tier=tier,
            score=score,
            blockers=blockers,
            enablers=enablers,
            reasoning=f"Score: {score}, Bloqueos: {len(blockers)}, Tier: {tier}",
            estimated_start_time_hours=est_start,
            can_start_now=can_start,
        )

    def filter(self, opportunities: list, tier: str | None = None):
        """Filter opportunities by zero-barrier tier. Returns generator of (opp, result)."""
        target_tier = tier or self.config.tier
        tier_order = ["absolute", "near_zero", "low", "filtered"]
        min_index = tier_order.index(target_tier) if target_tier in tier_order else 3

        for opp in opportunities:
            result = self.evaluate(opp)
            result_index = tier_order.index(result.tier) if result.tier in tier_order else 3
            if result_index <= min_index:
                yield opp, result

    def filter_list(self, opportunities: list, tier: str | None = None) -> list[Any]:
        """Return filtered list of opportunities."""
        return [opp for opp, _ in self.filter(opportunities, tier)]

    def get_stats(self, opportunities: list) -> dict:
        """Get zero-barrier statistics for a list."""
        results = [self.evaluate(opp) for opp in opportunities]
        total = len(results)
        if total == 0:
            return {"total": 0}

        by_tier = {}
        for r in results:
            by_tier[r.tier] = by_tier.get(r.tier, 0) + 1

        return {
            "total": total,
            "zero_barrier": sum(1 for r in results if r.is_zero_barrier),
            "can_start_now": sum(1 for r in results if r.can_start_now),
            "by_tier": by_tier,
            "avg_score": sum(r.score for r in results) / len(results) if results else 0,
            "common_blockers": self._common_blockers([r.blockers for r in results]),
        }

    def _common_blockers(self, all_blockers: list[list[str]]) -> list[tuple[str, int]]:
        from collections import Counter

        flat = [b for bl in all_blockers for b in bl]
        return Counter(flat).most_common(5)


# ──────────────────────────────────────────────────────────────────────
# Convenience
# ──────────────────────────────────────────────────────────────────────

_zero_barrier_engine: ZeroBarrierEngine | None = None


def get_zero_barrier_engine(config: ZeroBarrierConfig | None = None) -> ZeroBarrierEngine:
    global _zero_barrier_engine
    if _zero_barrier_engine is None:
        _zero_barrier_engine = ZeroBarrierEngine(config)
    return _zero_barrier_engine


def filter_zero_barrier(opportunities: list, tier: str = "absolute") -> list:
    """Convenience: filter to zero-barrier opportunities."""
    engine = get_zero_barrier_engine()
    return list(engine.filter(opportunities, tier=tier))


def is_zero_barrier(opportunity: Any, tier: str = "absolute") -> bool:
    """Quick check if opportunity is zero-barrier."""
    engine = get_zero_barrier_engine()
    result = engine.evaluate(opportunity)
    return result.is_zero_barrier
