"""Portfolio Optimizer — Optimal capital allocation with configurable objectives.

Optimizes configurable objectives:
- Risk-adjusted return
- Return / drawdown
- Return / volatility
- Sharpe
- Sortino
- Calmar
- Stability
- Capital efficiency

With constraints:
- Maximum drawdown
- Maximum leverage
- Maximum correlation
- Maximum exposure
- Minimum liquidity
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from core.trading.contracts import (
    AllocationMode,
    AllocationResult,
    MarketRegime,
    PerformanceMetrics,
    Strategy,
)

logger = logging.getLogger("ownex.trading.optimizer")


class OptimizationObjective(StrEnum):
    """Optimization objectives."""

    RISK_ADJUSTED_RETURN = "risk_adjusted_return"
    RETURN_OVER_DRAWDOWN = "return_over_drawdown"
    RETURN_OVER_VOLATILITY = "return_over_volatility"
    SHARPE = "sharpe"
    SORTINO = "sortino"
    CALMAR = "calmar"
    STABILITY = "stability"
    CAPITAL_EFFICIENCY = "capital_efficiency"


@dataclass
class OptimizationConstraint:
    """A constraint for optimization."""

    constraint_type: str  # max_drawdown, max_leverage, max_correlation, max_exposure, min_liquidity
    value: Decimal
    strict: bool = True  # If False, penalty instead of hard constraint


@dataclass
class PortfolioOptimizerConfig:
    """Configuration for portfolio optimizer."""

    objective: OptimizationObjective = OptimizationObjective.SHARPE
    constraints: list[OptimizationConstraint] = field(default_factory=list)
    max_strategies: int = 10
    min_allocation: Decimal = Decimal("0.01")  # 1% minimum
    max_allocation: Decimal = Decimal("0.30")  # 30% maximum per strategy
    cash_reserve: Decimal = Decimal("0.20")  # 20% cash reserve
    rebalance_threshold: Decimal = Decimal("0.05")  # 5% drift
    lookback_days: int = 252  # 1 year for metrics


class PortfolioOptimizer:
    """Optimizes portfolio allocation with configurable objectives and constraints."""

    def __init__(self, config: PortfolioOptimizerConfig | None = None):
        self.config = config or PortfolioOptimizerConfig()
        self._last_optimization: AllocationResult | None = None

    # ================================================================================═
    # MAIN OPTIMIZATION
    # ================================================================================

    def optimize(
        self,
        strategies: list[Strategy],
        performance_data: dict[str, PerformanceMetrics],
        correlation_matrix: dict[str, dict[str, Decimal]] | None = None,
        regime_performance: dict[str, dict[str, PerformanceMetrics]] | None = None,
        capital_state: dict[str, Decimal] | None = None,
    ) -> AllocationResult:
        """Run portfolio optimization."""

        # Filter strategies with performance data
        valid_strategies = [s for s in strategies if s.strategy_id in performance_data]
        if not valid_strategies:
            return AllocationResult(
                mode=AllocationMode.MANUAL,
                allocations={},
                total_allocated=Decimal("0"),
                cash_reserve=Decimal("0"),
            )

        # Extract metrics
        metrics = {s.strategy_id: performance_data[s.strategy_id] for s in valid_strategies}

        # Filter by minimum trades
        min_trades = 30
        metrics = {sid: m for sid, m in metrics.items() if m.number_of_trades >= min_trades}
        valid_strategies = [s for s in valid_strategies if s.strategy_id in metrics]

        if not metrics:
            return AllocationResult(
                mode=AllocationMode.MANUAL,
                allocations={},
                total_allocated=Decimal("0"),
                cash_reserve=Decimal("0"),
            )

        # Compute objective-specific scores
        scores = self._compute_scores(metrics)

        # Apply constraints
        scores = self._apply_constraints(scores, metrics, correlation_matrix)

        # Normalize to allocation
        allocations = self._normalize_allocations(scores, capital_state)

        # Compute total_allocated as Decimal explicitly
        total_allocated = sum(allocations.values(), Decimal("0"))

        # Compute cash_reserve
        cash_reserve = Decimal("0")
        if capital_state:
            available_cash = capital_state.get("available_cash", Decimal("0"))
            cash_reserve = max(Decimal("0"), available_cash - total_allocated)

        # Compute regime_exposure with proper typing
        regime_exposure: dict[MarketRegime, Decimal] = {}
        if regime_performance:
            regime_exposure = self._compute_regime_exposure(allocations, regime_performance)

        return AllocationResult(
            mode=AllocationMode.SHARPE_WEIGHTED,  # Will be set based on objective
            allocations=allocations,
            total_allocated=total_allocated,
            cash_reserve=cash_reserve,
            correlation_matrix=correlation_matrix or {},
            regime_exposure=regime_exposure,
        )

    # ================================================================================═
    # OBJECTIVE FUNCTIONS
    # ================================================================================

    def _compute_scores(self, metrics: dict[str, PerformanceMetrics]) -> dict[str, Decimal]:
        """Compute objective-specific scores for each strategy."""

        scores = {}

        for strategy_id, m in metrics.items():
            if self.config.objective == OptimizationObjective.SHARPE:
                scores[strategy_id] = max(Decimal("0"), m.sharpe)
            elif self.config.objective == OptimizationObjective.SORTINO:
                scores[strategy_id] = max(Decimal("0"), m.sortino)
            elif self.config.objective == OptimizationObjective.CALMAR:
                scores[strategy_id] = max(Decimal("0"), m.calmar)
            elif self.config.objective == OptimizationObjective.RETURN_OVER_DRAWDOWN:
                if m.max_drawdown > 0:
                    scores[strategy_id] = m.cagr / m.max_drawdown
                else:
                    scores[strategy_id] = Decimal("0")
            elif self.config.objective == OptimizationObjective.RETURN_OVER_VOLATILITY:
                if m.volatility > 0:
                    scores[strategy_id] = m.cagr / m.volatility
                else:
                    scores[strategy_id] = Decimal("0")
            elif self.config.objective == OptimizationObjective.STABILITY:
                # Stability = consistency of returns (win_rate * profit_factor as proxy)
                scores[strategy_id] = m.win_rate * m.profit_factor
            elif self.config.objective == OptimizationObjective.CAPITAL_EFFICIENCY:
                # Capital efficiency = return / exposure as proxy
                if m.exposure > 0:
                    scores[strategy_id] = m.cagr / m.exposure
                else:
                    scores[strategy_id] = m.cagr
            else:
                # Default: risk-adjusted return
                scores[strategy_id] = m.sharpe

        # Ensure non-negative
        return {k: max(Decimal("0"), v) for k, v in scores.items()}

    def _apply_constraints(
        self,
        scores: dict[str, Decimal],
        metrics: dict[str, PerformanceMetrics],
        correlation_matrix: dict[str, dict[str, Decimal]] | None = None,
    ) -> dict[str, Decimal]:
        """Apply hard constraints and penalties."""

        for constraint in self.config.constraints:
            if constraint.constraint_type == "max_drawdown":
                for sid, m in metrics.items():
                    if m.max_drawdown > constraint.value:
                        penalty = (m.max_drawdown - constraint.value) * Decimal("100")
                        if constraint.strict:
                            scores[sid] = Decimal("0")
                        else:
                            scores[sid] = max(Decimal("0"), scores[sid] - penalty)

            elif constraint.constraint_type == "max_leverage":
                # Would need leverage data per strategy
                pass

            elif constraint.constraint_type == "max_correlation" and correlation_matrix:
                # Penalize highly correlated strategies
                for sid1 in scores:
                    for sid2 in scores:
                        if sid1 != sid2:
                            corr = correlation_matrix.get(sid1, {}).get(sid2, Decimal("0"))
                            if corr > constraint.value:
                                penalty = (corr - constraint.value) * Decimal("50")
                                if constraint.strict:
                                    scores[sid1] = max(Decimal("0"), scores[sid1] - penalty)
                                    scores[sid2] = max(Decimal("0"), scores[sid2] - penalty)
                                else:
                                    scores[sid1] = max(Decimal("0"), scores[sid1] - penalty / 2)
                                    scores[sid2] = max(Decimal("0"), scores[sid2] - penalty / 2)

            elif constraint.constraint_type == "max_exposure":
                # Per-strategy exposure limit
                max_exp = constraint.value
                for sid, score in scores.items():
                    if score > max_exp:
                        if constraint.strict:
                            scores[sid] = max_exp
                        else:
                            scores[sid] = max(Decimal("0"), score - (score - max_exp) * Decimal("10"))

            elif constraint.constraint_type == "min_liquidity":
                # Would need liquidity data
                pass

        return scores

    def _normalize_allocations(
        self,
        scores: dict[str, Decimal],
        capital_state: dict[str, Decimal] | None = None,
    ) -> dict[str, Decimal]:
        """Normalize scores to capital allocations."""

        if not scores:
            return {}

        total_score = sum(scores.values())
        if total_score == 0:
            return {}

        # Available capital for allocation
        total_capital = capital_state.get("total_capital", Decimal("100000")) if capital_state else Decimal("100000")
        allocatable = total_capital * (Decimal("1") - self.config.cash_reserve)

        # Minimum and maximum per strategy
        min_alloc = allocatable * self.config.min_allocation
        max_alloc = allocatable * self.config.max_allocation

        # Initial allocation proportional to scores
        total_score = sum(scores.values())
        allocations = {}
        for sid, score in scores.items():
            alloc = (score / total_score) * allocatable
            alloc = max(min_alloc, min(max_alloc, alloc))
            allocations[sid] = alloc

        # If total exceeds allocatable, scale down
        total_alloc = sum(allocations.values())
        if total_alloc > allocatable:
            scale = allocatable / total_alloc
            allocations = {sid: a * scale for sid, a in allocations.items()}

        # Final check: enforce min/max again after scaling
        for sid in allocations:
            if allocations[sid] < min_alloc:
                allocations[sid] = Decimal("0")
            elif allocations[sid] > max_alloc:
                allocations[sid] = max_alloc

        return allocations

    def _compute_regime_exposure(
        self,
        allocations: dict[str, Decimal],
        regime_performance: dict[str, dict[str, PerformanceMetrics]] | None = None,
    ) -> dict[MarketRegime, Decimal]:
        """Compute capital exposure by market regime."""

        if not regime_performance:
            return {}

        regime_exposure: dict[MarketRegime, Decimal] = {}

        for sid, alloc in allocations.items():
            if sid in regime_performance:
                for regime_str, metrics in regime_performance[sid].items():
                    regime = MarketRegime(regime_str)
                    if regime not in regime_exposure:
                        regime_exposure[regime] = Decimal("0")
                    regime_exposure[regime] += alloc * (metrics.cagr / Decimal("100"))

        return regime_exposure

    # ================================================================================
    # REBALANCING
    # ================================================================================

    def check_rebalance_needed(
        self,
        current_allocations: dict[str, Decimal],
        target_allocations: dict[str, Decimal],
    ) -> tuple[bool, dict[str, Decimal]]:
        """Check if rebalancing is needed and return required trades."""

        trades = {}
        max_drift = Decimal("0")

        all_strategies = set(current_allocations.keys()) | set(target_allocations.keys())

        for sid in all_strategies:
            current = current_allocations.get(sid, Decimal("0"))
            target = target_allocations.get(sid, Decimal("0"))
            drift = abs(current - target)

            if drift > self.config.rebalance_threshold:
                trades[sid] = target - current
                max_drift = max(max_drift, drift)

        return len(trades) > 0, trades

    # ================================================================================════
    # SINGLETON
    # ================================================================================═══


_portfolio_optimizer: PortfolioOptimizer | None = None


def get_portfolio_optimizer(config: PortfolioOptimizerConfig | None = None) -> PortfolioOptimizer:
    """Get the global portfolio optimizer singleton."""
    global _portfolio_optimizer
    if _portfolio_optimizer is None:
        _portfolio_optimizer = PortfolioOptimizer(config)
    return _portfolio_optimizer


_portfolio_optimizer: PortfolioOptimizer | None = None
