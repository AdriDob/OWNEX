"""Kelly Provider — optimal stake sizing calculations.

Provides the ``KellyProvider`` class referenced by the ODYSSEY app
(``apps/odyssey/engines/kelly.py`` and ``apps/odyssey/api/routers.py``).
"""

from __future__ import annotations

import math


class KellyProvider:
    """Calculate Kelly-optimal stake fractions from decimal odds and win probability."""

    @staticmethod
    def calculate(odds: float, win_probability: float, bankroll: float, fraction: float = 0.25) -> dict:
        """Compute Kelly criterion values.

        Args:
            odds: Decimal odds (e.g. 2.0 = even money).
            win_probability: Estimated probability of winning (0..1).
            bankroll: Current bankroll amount.
            fraction: Fraction of full Kelly to stake (safety factor).

        Returns:
            dict with ``full_kelly``, ``fractional_kelly``, ``stake_amount``,
            ``ev``, ``growth_rate``.
        """
        odds = float(odds)
        win_probability = float(win_probability)
        bankroll = float(bankroll)
        fraction = float(fraction)

        if odds <= 1 or win_probability <= 0 or win_probability >= 1:
            return {
                "full_kelly": 0.0,
                "fractional_kelly": 0.0,
                "stake_amount": 0.0,
                "ev": 0.0,
                "growth_rate": 0.0,
            }

        b = odds - 1.0  # net odds
        q = 1.0 - win_probability

        full_kelly = (b * win_probability - q) / b if b > 0 else 0.0
        full_kelly = max(0.0, full_kelly)

        fractional_kelly = full_kelly * fraction
        stake_amount = bankroll * fractional_kelly

        ev = b * win_probability - q

        # Expected log growth rate of the Kelly stake
        growth_rate = 0.0
        if full_kelly > 0 and 1 + b * fractional_kelly > 0:
            growth_rate = win_probability * math.log1p(b * fractional_kelly) + q * math.log1p(-fractional_kelly)

        return {
            "full_kelly": round(full_kelly, 4),
            "fractional_kelly": round(fractional_kelly, 4),
            "stake_amount": round(stake_amount, 2),
            "ev": round(ev, 4),
            "growth_rate": round(growth_rate, 4),
        }
