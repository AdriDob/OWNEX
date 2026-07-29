from __future__ import annotations

import logging
from typing import Any

from core.financial_intelligence.models import Opportunity

logger = logging.getLogger("orion.financial_intelligence.opportunity_engine")


# ── Scoring weights ─────────────────────────────────────────────

DEFAULT_WEIGHTS: dict[str, float] = {
    "expected_value": 0.25,
    "historical_win_rate": 0.15,
    "confidence_interval_quality": 0.10,
    "risk_adjusted_return": 0.15,
    "liquidity": 0.10,
    "execution_complexity": -0.10,
    "market_regime_favorability": 0.10,
    "model_confidence": 0.10,
    "data_quality": 0.05,
}


def _regime_favorability(regime: str) -> float:
    return {"bull": 0.8, "bear": 0.2, "sideways": 0.5, "volatile": 0.3}.get(regime, 0.5)


class OpportunityEngine:
    """Ranks financial opportunities by expected value, risk, and consensus.

    Every opportunity receives a composite priority_score using configurable
    weighted factors. Only top-ranked opportunities move forward to the
    multi-agent decision model.
    """

    def __init__(self, weights: dict[str, float] | None = None):
        self._weights = weights or dict(DEFAULT_WEIGHTS)
        self._history: list[Opportunity] = []

    def score(self, opp: Opportunity) -> float:
        ci_range = opp.confidence_interval[1] - opp.confidence_interval[0]
        ci_quality = max(0.0, 1.0 - (ci_range / max(opp.expected_value, 0.01)))

        risk_adj = opp.expected_value * opp.historical_win_rate / max(opp.risk_score, 0.01)
        norm_risk_adj = min(risk_adj / 100.0, 1.0)

        raw = (
            self._weights.get("expected_value", 0) * min(opp.expected_value / 10000.0, 1.0)
            + self._weights.get("historical_win_rate", 0) * opp.historical_win_rate
            + self._weights.get("confidence_interval_quality", 0) * ci_quality
            + self._weights.get("risk_adjusted_return", 0) * norm_risk_adj
            + self._weights.get("liquidity", 0) * opp.liquidity
            + self._weights.get("execution_complexity", 0) * opp.execution_complexity
            + self._weights.get("market_regime_favorability", 0) * _regime_favorability(opp.market_regime)
            + self._weights.get("model_confidence", 0) * opp.model_confidence
            + self._weights.get("data_quality", 0) * opp.data_quality
        )
        return max(0.0, min(round(raw, 4), 1.0))

    def evaluate(self, opportunity: Opportunity) -> Opportunity:
        opportunity.priority_score = self.score(opportunity)
        if opportunity.risk_score > 0.8:
            opportunity.rejected_reasons.append("Risk score exceeds 0.8 threshold")
        if opportunity.execution_complexity > 0.9:
            opportunity.rejected_reasons.append("Execution complexity exceeds 0.9 threshold")
        if opportunity.model_confidence < 0.2:
            opportunity.rejected_reasons.append("Model confidence below 0.2 minimum")
        self._history.append(opportunity)
        return opportunity

    def rank(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        scored = [self.evaluate(o) for o in opportunities]
        scored.sort(key=lambda o: o.priority_score, reverse=True)
        return scored

    def top_n(self, opportunities: list[Opportunity], n: int = 5) -> list[Opportunity]:
        return self.rank(opportunities)[:n]

    def get_statistics(self) -> dict[str, Any]:
        if not self._history:
            return {"total_evaluated": 0}
        scores = [o.priority_score for o in self._history]
        return {
            "total_evaluated": len(self._history),
            "avg_score": round(sum(scores) / len(scores), 4),
            "max_score": round(max(scores), 4),
            "min_score": round(min(scores), 4),
            "top_sources": self._top_sources(),
        }

    def _top_sources(self) -> list[dict[str, Any]]:
        from collections import Counter

        counts: Counter = Counter(o.source for o in self._history)
        return [{"source": s, "count": c} for s, c in counts.most_common(5)]
