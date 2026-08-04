"""Odds Engine — odds conversion and fair value calculation."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("orion.odyssey.engines.odds")


@dataclass
class OddsConversion:
    decimal: float = 0.0
    american: int = 0
    fractional: str = ""
    implied_prob: float = 0.0
    fair_prob: float = 0.0
    vig: float = 0.0


class OddsEngine:
    """Convert and analyze odds from any format."""

    @staticmethod
    def decimal_to_american(decimal: float) -> int:
        if decimal <= 1.0:
            return 0
        if decimal >= 2.0:
            return round((decimal - 1.0) * 100)
        return round(-100 / (decimal - 1.0))

    @staticmethod
    def decimal_to_fractional(decimal: float) -> str:
        if decimal <= 1.0:
            return "0/1"
        from fractions import Fraction

        f = Fraction(decimal - 1.0).limit_denominator(100)
        return f"{f.numerator}/{f.denominator}"

    @staticmethod
    def implied_probability(decimal: float) -> float:
        return 1.0 / decimal if decimal > 0 else 0.0

    @staticmethod
    def fair_odds(prob: float) -> float:
        return 1.0 / prob if prob > 0 else 0.0

    def convert(self, decimal: float) -> OddsConversion:
        implied = self.implied_probability(decimal)
        return OddsConversion(
            decimal=round(decimal, 2),
            american=self.decimal_to_american(decimal),
            fractional=self.decimal_to_fractional(decimal),
            implied_prob=round(implied * 100, 2),
            fair_prob=implied,
            vig=0.0,
        )

    def remove_vig(self, odds_1: float, odds_2: float) -> tuple[float, float]:
        """Remove overround (vig) from a two-outcome market."""
        imp1 = self.implied_probability(odds_1)
        imp2 = self.implied_probability(odds_2)
        total_imp = imp1 + imp2
        if total_imp <= 0:
            return odds_1, odds_2
        fair1 = self.fair_odds(imp1 / total_imp)
        fair2 = self.fair_odds(imp2 / total_imp)
        return round(fair1, 4), round(fair2, 4)
