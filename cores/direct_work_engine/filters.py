"""Strict Filtering — hard rejection gate for the Opportunity Intelligence Engine.

Complementary to the continuous Zero Barrier spectrum. Where the scorer measures
*how low* the entry barrier is, the StrictFilter decides *whether to even look*:
it hard-rejects opportunities that carry red flags (unclear payment, fake
rewards, unpaid mandatory work, non-remote restrictions, excessive hiring
process). The spec rule applies here — 10 excellent opportunities beat 1000
useless ones.
"""

from __future__ import annotations

from cores.direct_work_engine.models import Opportunity, PaymentMethod

# A "reward" below this amount is not real money (vanity / fake bounty).
_MIN_CREDIBLE_REWARD_USD: float = 2.0

# A remote opportunity that is not remote is a category-killer (location-bound).
# Long payout windows and gift-card-only payouts are the classic scam vectors.


class StrictFilter:
    """Deterministic hard-reject rules. Returns empty reasons = opportunity passes."""

    def reject(self, opp: Opportunity) -> list[str]:
        """Return the list of rejection reasons for an opportunity (empty = approved)."""
        reasons: list[str] = []

        # Unclear / fake payment
        if opp.payment < 0:
            reasons.append("unclear_payment: reward value is negative")
        elif opp.payment == 0:
            reasons.append("unclear_payment: no reward published")
        elif opp.payment < _MIN_CREDIBLE_REWARD_USD:
            reasons.append(f"unclear_payment: reward below credible minimum (${_MIN_CREDIBLE_REWARD_USD:.0f})")

        # Unpaid mandatory work: significant effort with no compensation.
        if opp.payment <= 0 and opp.estimated_time_hours >= 4:
            reasons.append("unpaid_mandatory_work: 4+h expected with no reward")

        # Impossible country restrictions: OWNEX targets remote, open-world work.
        if not opp.remote:
            reasons.append("not_remote: country/location restriction blocks delivery")

        # Suspicious payout channels: gift cards only is a scam/abuse signal.
        if opp.payment_method == PaymentMethod.GIFT_CARD and opp.payment > 0:
            reasons.append("suspicious_platform: only gift-card payout for a cash task")

        # Excessive application process: portfolio + interview + registration is a
        # hiring funnel, not a zero-barrier opportunity.
        if opp.interview_required and opp.portfolio_required and opp.registration_required:
            reasons.append("excessive_application_process: interview + portfolio + registration required")

        return reasons

    def is_rejected(self, opp: Opportunity) -> bool:
        """True when the opportunity must be hard-rejected."""
        return bool(self.reject(opp))

    def validate(self, opportunities: list[Opportunity]) -> dict[str, list[str]]:
        """Classify a batch: returns a mapping of opportunity id -> rejection reasons.

        Opportunities absent from the mapping passed the strict gate.
        """
        return {opp.id: self.reject(opp) for opp in opportunities if self.reject(opp)}
