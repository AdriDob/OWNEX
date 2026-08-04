"""Term / Negotiation intelligence — analyzes the commercial terms of an opportunity.

The Negotiation Agent decides whether to accept, negotiate or decline based on
effective hourly rate, payment-method reliability and payout speed. Pure and
decoupled: no side effects, no network.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from cores.direct_work_engine.models import PAYMENT_RELIABILITY, Opportunity

logger = logging.getLogger("ownex.direct_work_engine.negotiation")

# Reference USD/hour used to judge payment quality.
_FAIR_RATE: float = 50.0
_MIN_RATE: float = 20.0
_SLOW_PAYOUT_DAYS: float = 30.0
_RISKY_PAYMENT_RISK: float = 0.5


@dataclass(slots=True)
class TermAssessment:
    """Commercial assessment of one opportunity's terms."""

    opportunity_id: str
    verdict: str  # accept | negotiate | decline
    payment_quality: float = 0.0
    payment_method_risk: float = 0.0
    effective_rate_usd_per_hour: float = 0.0
    terms_issues: list[str] = field(default_factory=list)
    negotiation_leverage: list[str] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)


class TermAnalyzer:
    """Rates the terms of an opportunity and recommends a negotiation stance."""

    def assess(self, opportunity: Opportunity) -> TermAssessment:
        hours = max(opportunity.estimated_time_hours or 1.0, 1.0)
        rate = opportunity.payment / hours
        payment_quality = min(1.0, rate / _FAIR_RATE)

        reliability = PAYMENT_RELIABILITY.get(opportunity.payment_method, 0.5)
        payment_method_risk = 1.0 - reliability

        issues = self._build_issues(opportunity, rate, payment_method_risk)
        leverage = self._build_leverage(opportunity)

        if not issues:
            verdict = "accept"
        elif rate < _MIN_RATE and payment_method_risk > _RISKY_PAYMENT_RISK:
            verdict = "decline"
        else:
            verdict = "negotiate"

        reasoning = [
            f"Effective rate: ${rate:.0f}/h (quality {payment_quality:.0%})",
            f"Payment method risk: {payment_method_risk:.0%}",
        ]
        if issues:
            reasoning.append("Issues: " + "; ".join(issues[:3]))
        if leverage:
            reasoning.append("Leverage: " + "; ".join(leverage[:2]))

        return TermAssessment(
            opportunity_id=opportunity.id,
            verdict=verdict,
            payment_quality=round(payment_quality, 3),
            payment_method_risk=round(payment_method_risk, 3),
            effective_rate_usd_per_hour=round(rate, 2),
            terms_issues=issues,
            negotiation_leverage=leverage,
            reasoning=reasoning,
        )

    @staticmethod
    def _build_issues(opp: Opportunity, rate: float, payment_method_risk: float) -> list[str]:
        issues: list[str] = []
        if rate < _MIN_RATE:
            issues.append(f"Effective rate ${rate:.0f}/h is below the ${_MIN_RATE:.0f}/h minimum")
        elif rate < _FAIR_RATE:
            issues.append(f"Effective rate ${rate:.0f}/h is below the ${_FAIR_RATE:.0f}/h fair reference")
        if payment_method_risk > _RISKY_PAYMENT_RISK:
            issues.append(f"Payment method '{opp.payment_method.value}' has limited reliability")
        if opp.time_to_payout_days is not None and opp.time_to_payout_days > _SLOW_PAYOUT_DAYS:
            issues.append(f"Slow payout: {int(opp.time_to_payout_days)} days")
        if opp.interview_required:
            issues.append("Interview required — not purely outcome-based")
        return issues

    @staticmethod
    def _build_leverage(opp: Opportunity) -> list[str]:
        leverage: list[str] = []
        if opp.payment_proven:
            leverage.append("Platform payment history verified")
        if opp.accepts_individuals:
            leverage.append("Accepts individuals — no corporate middleman")
        if opp.asynchronous:
            leverage.append("Asynchronous — work on own schedule")
        return leverage
