"""Ensemble Intelligence — Strategy scoring, correlation analysis, and portfolio optimization.

The system should NOT simply select "strategy with highest return."
Instead calculate a composite score considering multiple factors.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from core.trading.contracts import (
    MarketRegime,
    PerformanceMetrics,
    Strategy,
)

logger = logging.getLogger("ownex.trading.ensemble")


@dataclass
class StrategyScore:
    """Composite score for a strategy."""

    strategy_id: str
    engine_id: str

    # Component scores (0-100)
    return_score: Decimal = Decimal("0")
    risk_adjusted_score: Decimal = Decimal("0")
    consistency_score: Decimal = Decimal("0")
    liquidity_score: Decimal = Decimal("0")
    execution_quality_score: Decimal = Decimal("0")
    robustness_score: Decimal = Decimal("0")

    # Penalties
    drawdown_penalty: Decimal = Decimal("0")
    overfit_penalty: Decimal = Decimal("0")
    correlation_penalty: Decimal = Decimal("0")
    fee_penalty: Decimal = Decimal("0")
    slippage_penalty: Decimal = Decimal("0")
    data_quality_penalty: Decimal = Decimal("0")

    # Composite
    composite_score: Decimal = Decimal("0")
    rank: int = 0

    # Regime-specific
    regime_scores: dict[str, Decimal] = field(default_factory=dict)

    # Metadata
    computed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class CorrelationMatrix:
    """Strategy correlation matrix."""

    correlations: dict[str, dict[str, Decimal]] = field(default_factory=dict)
    computed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def get_correlation(self, strategy_a: str, strategy_b: str) -> Decimal:
        return self.correlations.get(strategy_a, {}).get(strategy_b, Decimal("0"))

    def get_diversifiers(self, threshold: Decimal = Decimal("0.3")) -> list[tuple[str, str]]:
        """Get pairs of strategies with low correlation (good diversifiers)."""
        diversifiers = []
        strategies = list(self.correlations.keys())
        for i, s1 in enumerate(strategies):
            for s2 in strategies[i + 1 :]:
                corr = self.get_correlation(s1, s2)
                if corr < threshold:
                    diversifiers.append((s1, s2))
        return diversifiers

    def get_duplicates(self, threshold: Decimal = Decimal("0.7")) -> list[tuple[str, str]]:
        """Get pairs of highly correlated strategies (duplicates)."""
        duplicates = []
        strategies = list(self.correlations.keys())
        for i, s1 in enumerate(strategies):
            for s2 in strategies[i + 1 :]:
                corr = self.get_correlation(s1, s2)
                if corr > threshold:
                    duplicates.append((s1, s2))
        return duplicates


class EnsembleIntelligence:
    """Calculates composite scores and manages ensemble allocation."""

    def __init__(self):
        self._scores: dict[str, StrategyScore] = {}
        self._correlation_matrix: CorrelationMatrix | None = None

    # ═════════════════════════════════════════════════════════════════════════
    # SCORING
    # ════════════════════════════════════════════════════════════════════════

    def calculate_scores(
        self,
        strategies: list[Strategy],
        performance_data: dict[str, PerformanceMetrics],
        regime_performance: dict[str, dict[MarketRegime, PerformanceMetrics]] | None = None,
        correlation_matrix: CorrelationMatrix | None = None,
    ) -> dict[str, StrategyScore]:
        """Calculate composite scores for all strategies."""

        self._correlation_matrix = correlation_matrix
        scores = {}

        for strategy in strategies:
            metrics = performance_data.get(strategy.strategy_id)
            if not metrics:
                continue

            score = self._calculate_strategy_score(strategy, metrics, regime_performance)
            scores[strategy.strategy_id] = score

        # Apply correlation penalties
        if correlation_matrix:
            self._apply_correlation_penalties(scores, correlation_matrix)

        # Rank strategies
        ranked = sorted(scores.values(), key=lambda s: s.composite_score, reverse=True)
        for i, score in enumerate(ranked):
            score.rank = i + 1

        self._scores = {s.strategy_id: s for s in ranked}
        return self._scores

    def _calculate_strategy_score(
        self,
        strategy: Strategy,
        metrics: PerformanceMetrics,
        regime_performance: dict[str, dict[MarketRegime, PerformanceMetrics]] | None = None,
    ) -> StrategyScore:
        """Calculate composite score for a single strategy."""

        score = StrategyScore(strategy_id=strategy.strategy_id, engine_id=strategy.engine_id)

        # Return score (CAGR-based)
        score.return_score = self._normalize_return(metrics.cagr)

        # Risk-adjusted score (Sharpe-based)
        score.risk_adjusted_score = self._normalize_sharpe(metrics.sharpe)

        # Consistency score (win rate + profit factor)
        score.consistency_score = self._normalize_consistency(metrics.win_rate, metrics.profit_factor)

        # Liquidity score (turnover, time in market)
        score.liquidity_score = self._normalize_liquidity(metrics.turnover, metrics.time_in_market)

        # Execution quality (slippage, fees)
        score.execution_quality_score = self._normalize_execution_quality(metrics.slippage, metrics.fees)

        # Robustness (based on validation phases passed, regime performance)
        score.robustness_score = self._calculate_robustness(strategy, regime_performance)

        # Calculate penalties
        score.drawdown_penalty = self._calculate_drawdown_penalty(metrics.max_drawdown)
        score.overfit_penalty = self._calculate_overfit_penalty(strategy)
        score.correlation_penalty = Decimal("0")  # Applied later
        score.fee_penalty = self._calculate_fee_penalty(metrics.fees, metrics.turnover)
        score.slippage_penalty = self._calculate_slippage_penalty(metrics.slippage)
        score.data_quality_penalty = self._calculate_data_quality_penalty(strategy)

        # Calculate composite score
        score.composite_score = self._compute_composite(score)

        # Regime-specific scores
        if regime_performance and strategy.strategy_id in regime_performance:
            for regime, regime_metrics in regime_performance[strategy.strategy_id].items():
                regime_score = self._normalize_return(regime_metrics.cagr)
                score.regime_scores[regime.value] = regime_score

        return score

    def _normalize_return(self, cagr: Decimal) -> Decimal:
        """Normalize CAGR to 0-100 scale."""
        # 50% CAGR = 100, 0% = 50, -50% = 0
        return max(Decimal("0"), min(Decimal("100"), (cagr + Decimal("0.5")) * Decimal("100")))

    def _normalize_sharpe(self, sharpe: Decimal) -> Decimal:
        """Normalize Sharpe to 0-100 scale."""
        # Sharpe 3 = 100, 1 = 50, 0 = 25
        return max(Decimal("0"), min(Decimal("100"), (sharpe + Decimal("1")) * Decimal("25")))

    def _normalize_consistency(self, win_rate: Decimal, profit_factor: Decimal) -> Decimal:
        """Normalize consistency (win rate * profit factor)."""
        consistency = (win_rate / Decimal("100")) * min(profit_factor, Decimal("3"))
        return min(Decimal("100"), consistency * Decimal("50"))

    def _normalize_liquidity(self, turnover: Decimal, time_in_market: Decimal) -> Decimal:
        """Normalize liquidity score."""
        # High turnover + high time in market = good liquidity
        return min(Decimal("100"), (turnover / Decimal("10")) * Decimal("100"))

    def _normalize_execution_quality(self, slippage: Decimal, fees: Decimal) -> Decimal:
        """Normalize execution quality (lower is better)."""
        cost = slippage + fees / Decimal("10000")
        return max(Decimal("0"), Decimal("100") - cost * Decimal("1000"))

    def _calculate_robustness(
        self,
        strategy: Strategy,
        regime_performance: dict[str, dict[MarketRegime, PerformanceMetrics]] | None = None,
    ) -> Decimal:
        """Calculate robustness score based on validation phases and regime performance."""
        score = Decimal("50")  # Base

        # Check validation phases
        passed_phases = sum(1 for v in strategy.validation_status.values() if v)
        score += passed_phases * Decimal("5")

        # Check regime consistency
        if regime_performance and strategy.strategy_id in regime_performance:
            regimes = regime_performance[strategy.strategy_id]
            if len(regimes) >= 3:
                # Check if profitable in multiple regimes
                profitable_regimes = sum(1 for m in regimes.values() if m.cagr > 0)
                score += profitable_regimes * Decimal("5")

        return min(Decimal("100"), score)

    def _calculate_drawdown_penalty(self, max_drawdown: Decimal) -> Decimal:
        """Penalty for excessive drawdown."""
        if max_drawdown > Decimal("0.3"):
            return (max_drawdown - Decimal("0.3")) * Decimal("100")
        return Decimal("0")

    def _calculate_overfit_penalty(self, strategy: Strategy) -> Decimal:
        """Penalty for overfitting indicators."""
        param_count = len(strategy.parameters)
        if param_count > 10:
            return Decimal(str(param_count - 10)) * Decimal("5")
        return Decimal("0")

    def _calculate_correlation_penalty(self, score: StrategyScore, matrix: CorrelationMatrix) -> Decimal:
        """Penalty for correlation with other strategies."""
        duplicates = matrix.get_duplicates(Decimal("0.7"))
        penalty = Decimal("0")
        for s1, s2 in duplicates:
            if s1 == score.strategy_id or s2 == score.strategy_id:
                penalty += Decimal("10")
        return penalty

    def _calculate_fee_penalty(self, fees: Decimal, turnover: Decimal) -> Decimal:
        """Penalty for high fees relative to turnover."""
        if turnover == 0:
            return Decimal("0")
        fee_rate = fees / turnover
        if fee_rate > Decimal("0.01"):  # 1%
            return (fee_rate - Decimal("0.01")) * Decimal("1000")
        return Decimal("0")

    def _calculate_slippage_penalty(self, slippage: Decimal) -> Decimal:
        """Penalty for excessive slippage."""
        if slippage > Decimal("0.005"):  # 0.5%
            return (slippage - Decimal("0.005")) * Decimal("10000")
        return Decimal("0")

    def _calculate_data_quality_penalty(self, strategy: Strategy) -> Decimal:
        """Penalty for data quality issues."""
        # Would check data source, sample size, etc.
        return Decimal("0")

    def _compute_composite(self, score: StrategyScore) -> Decimal:
        """Compute composite score from components."""

        # Weights for components
        weights = {
            "return": Decimal("0.25"),
            "risk_adjusted": Decimal("0.20"),
            "consistency": Decimal("0.15"),
            "liquidity": Decimal("0.10"),
            "execution": Decimal("0.10"),
            "robustness": Decimal("0.20"),
        }

        composite = (
            score.return_score * weights["return"]
            + score.risk_adjusted_score * weights["risk_adjusted"]
            + score.consistency_score * weights["consistency"]
            + score.liquidity_score * weights["liquidity"]
            + score.execution_quality_score * weights["execution"]
            + score.robustness_score * weights["robustness"]
        )

        # Subtract penalties
        penalties = (
            score.drawdown_penalty
            + score.overfit_penalty
            + score.correlation_penalty
            + score.fee_penalty
            + score.slippage_penalty
            + score.data_quality_penalty
        )

        return max(Decimal("0"), composite - penalties)

    def _apply_correlation_penalties(
        self,
        scores: dict[str, StrategyScore],
        matrix: CorrelationMatrix,
    ) -> None:
        """Apply correlation penalties to scores."""
        for score in scores.values():
            score.correlation_penalty = self._calculate_correlation_penalty(score, matrix)
            score.composite_score = max(Decimal("0"), score.composite_score - score.correlation_penalty)

    # ═════════════════════════════════════════════════════════════════════════
    # QUERIES
    # ════════════════════════════════════════════════════════════════════════

    def get_top_strategies(self, n: int = 10) -> list[StrategyScore]:
        """Get top N strategies by composite score."""
        return sorted(self._scores.values(), key=lambda s: s.composite_score, reverse=True)[:n]

    def get_strategy_score(self, strategy_id: str) -> StrategyScore | None:
        return self._scores.get(strategy_id)

    def get_scores_by_regime(self, regime: str) -> list[StrategyScore]:
        """Get strategies ranked by performance in a specific regime."""
        scored = []
        for score in self._scores.values():
            if regime in score.regime_scores:
                scored.append((score.regime_scores[regime], score))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored]


# ══════════════════════════════════════════════════════════════════════════
# CORRELATION ANALYSIS
# ═════════════════════════════════════════════════════════════════════════


class CorrelationAnalyzer:
    """Analyzes strategy correlations to identify diversifiers and duplicates."""

    def __init__(self):
        self._matrix: CorrelationMatrix | None = None

    def compute_correlation_matrix(
        self,
        strategies: list[Strategy],
        returns_data: dict[str, list[Decimal]],
    ) -> CorrelationMatrix:
        """Compute correlation matrix from returns data."""

        strategy_ids = [s.strategy_id for s in strategies if s.strategy_id in returns_data]
        correlations: dict[str, dict[str, Decimal]] = {sid: {} for sid in strategy_ids}

        for i, s1 in enumerate(strategy_ids):
            returns1 = returns_data[s1]
            for j, s2 in enumerate(strategy_ids):
                if i == j:
                    correlations[s1][s2] = Decimal("1")
                elif j > i:
                    returns2 = returns_data[s2]
                    corr = self._pearson_correlation(returns1, returns2)
                    correlations[s1][s2] = corr
                    correlations[s2][s1] = corr

        self._matrix = CorrelationMatrix(correlations=correlations)
        return self._matrix

    def _pearson_correlation(self, x: list[Decimal], y: list[Decimal]) -> Decimal:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return Decimal("0")

        n = Decimal(str(len(x)))
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(len(x)))
        sum_x2 = sum(v * v for v in x)
        sum_y2 = sum(v * v for v in y)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)).sqrt()

        if denominator == 0:
            return Decimal("0")

        return numerator / denominator

    def get_diversifiers(self, threshold: Decimal = Decimal("0.3")) -> list[tuple[str, str]]:
        """Get strategy pairs that are good diversifiers."""
        if not self._matrix:
            return []
        return self._matrix.get_diversifiers(threshold)

    def get_duplicates(self, threshold: Decimal = Decimal("0.7")) -> list[tuple[str, str]]:
        """Get highly correlated strategy pairs (duplicates)."""
        if not self._matrix:
            return []
        return self._matrix.get_duplicates(threshold)

    def get_correlation(self, strategy_a: str, strategy_b: str) -> Decimal:
        if not self._matrix:
            return Decimal("0")
        return self._matrix.get_correlation(strategy_a, strategy_b)


# ══════════════════════════════════════════════════════════════════════════
# SINGLETONS
# ═════════════════════════════════════════════════════════════════════════

_ensemble_intelligence: EnsembleIntelligence | None = None
_correlation_analyzer: CorrelationAnalyzer | None = None


def get_ensemble_intelligence() -> EnsembleIntelligence:
    global _ensemble_intelligence
    if _ensemble_intelligence is None:
        _ensemble_intelligence = EnsembleIntelligence()
    return _ensemble_intelligence


def get_correlation_analyzer() -> CorrelationAnalyzer:
    global _correlation_analyzer
    if _correlation_analyzer is None:
        _correlation_analyzer = CorrelationAnalyzer()
    return _correlation_analyzer
