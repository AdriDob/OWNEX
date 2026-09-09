"""Capital Engine — Single authoritative capital allocation and tracking.

ONE canonical capital model. All strategies consume capital through this layer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from core.trading.contracts import (
    AllocationMode,
    AllocationResult,
    Strategy,
)

logger = logging.getLogger("ownex.trading.capital")


@dataclass
class CapitalState:
    """Current capital state."""

    total_capital: Decimal = Decimal("0")
    available_cash: Decimal = Decimal("0")
    reserved_cash: Decimal = Decimal("0")
    invested_capital: Decimal = Decimal("0")
    margin_used: Decimal = Decimal("0")
    equity: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    fees_paid: Decimal = Decimal("0")
    funding_paid: Decimal = Decimal("0")
    withdrawals: Decimal = Decimal("0")
    deposits: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    max_drawdown: Decimal = Decimal("0")
    current_drawdown: Decimal = Decimal("0")
    portfolio_value: Decimal = Decimal("0")
    total_exposure: Decimal = Decimal("0")
    leverage: Decimal = Decimal("0")
    liquidation_distance: Decimal = Decimal("0")
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class StrategyAllocation:
    """Capital allocation for a single strategy."""

    strategy_id: str
    allocated: Decimal = Decimal("0")
    used: Decimal = Decimal("0")
    available: Decimal = Decimal("0")
    max_allocation: Decimal = Decimal("0")
    current_exposure: Decimal = Decimal("0")
    pnl: Decimal = Decimal("0")
    status: str = "active"  # active, paused, liquidating


class CapitalEngine:
    """Single authoritative capital engine.

    Manages all capital allocation, tracking, and rebalancing.
    """

    def __init__(self, initial_capital: Decimal = Decimal("0")):
        self.state = CapitalState(total_capital=initial_capital, available_cash=initial_capital)
        self.allocations: dict[str, StrategyAllocation] = {}
        self._allocation_mode = AllocationMode.MANUAL
        self._rebalance_threshold = Decimal("0.05")  # 5% drift triggers rebalance
        self._last_rebalance = datetime.now(UTC).isoformat()

    # ════════════════════════════════════════════════════════════════════════
    # CAPITAL MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def deposit(self, amount: Decimal, source: str = "manual") -> bool:
        """Add capital to the system."""
        if amount <= 0:
            return False
        self.state.total_capital += amount
        self.state.available_cash += amount
        self.state.deposits += amount
        self._recalculate_equity()
        logger.info(f"Deposited {amount} from {source}")
        return True

    def withdraw(self, amount: Decimal, destination: str = "manual") -> bool:
        """Withdraw capital from available cash."""
        if amount <= 0 or amount > self.state.available_cash:
            return False
        self.state.available_cash -= amount
        self.state.total_capital -= amount
        self.state.withdrawals += amount
        self._recalculate_equity()
        logger.info(f"Withdrew {amount} to {destination}")
        return True

    def add_realized_pnl(self, amount: Decimal) -> None:
        """Add realized P&L."""
        self.state.realized_pnl += amount
        self.state.net_profit += amount
        self.state.available_cash += amount
        self._recalculate_equity()

    def add_unrealized_pnl(self, amount: Decimal) -> None:
        """Update unrealized P&L."""
        self.state.unrealized_pnl = amount
        self._recalculate_equity()

    def add_fees(self, amount: Decimal) -> None:
        """Add fees paid."""
        self.state.fees_paid += amount
        self.state.available_cash -= amount
        self._recalculate_equity()

    def add_funding(self, amount: Decimal) -> None:
        """Add funding paid/received."""
        self.state.funding_paid += amount
        self.state.available_cash -= amount
        self._recalculate_equity()

    def add_margin(self, amount: Decimal) -> None:
        """Add margin used."""
        self.state.margin_used += amount
        self.state.available_cash -= amount
        self._recalculate_equity()

    def release_margin(self, amount: Decimal) -> None:
        """Release margin back to available cash."""
        self.state.margin_used = max(Decimal("0"), self.state.margin_used - amount)
        self.state.available_cash += amount
        self._recalculate_equity()

    # ════════════════════════════════════════════════════════════════════════
    # ALLOCATION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def allocate_strategy(self, strategy_id: str, amount: Decimal, max_allocation: Decimal | None = None) -> bool:
        """Allocate capital to a strategy."""
        if amount <= 0 or amount > self.state.available_cash:
            return False

        if max_allocation is None:
            max_allocation = amount

        if strategy_id in self.allocations:
            alloc = self.allocations[strategy_id]
            alloc.allocated += amount
            alloc.max_allocation = max(alloc.max_allocation, max_allocation)
        else:
            self.allocations[strategy_id] = StrategyAllocation(
                strategy_id=strategy_id,
                allocated=amount,
                max_allocation=max_allocation,
                available=amount,
            )

        self.state.available_cash -= amount
        self.state.invested_capital += amount
        self._recalculate_equity()
        logger.info(f"Allocated {amount} to strategy {strategy_id}")
        return True

    def deallocate_strategy(self, strategy_id: str, amount: Decimal | None = None) -> bool:
        """Deallocate capital from a strategy."""
        if strategy_id not in self.allocations:
            return False

        alloc = self.allocations[strategy_id]
        dealloc_amount = amount or alloc.allocated

        if dealloc_amount > alloc.allocated:
            dealloc_amount = alloc.allocated

        alloc.allocated -= dealloc_amount
        alloc.available = max(Decimal("0"), alloc.available - dealloc_amount)
        self.state.invested_capital -= dealloc_amount
        self.state.available_cash += dealloc_amount

        if alloc.allocated <= 0:
            del self.allocations[strategy_id]

        self._recalculate_equity()
        logger.info(f"Deallocated {dealloc_amount} from strategy {strategy_id}")
        return True

    def update_strategy_usage(self, strategy_id: str, used: Decimal, pnl: Decimal, exposure: Decimal) -> None:
        """Update strategy capital usage."""
        if strategy_id not in self.allocations:
            return

        alloc = self.allocations[strategy_id]
        alloc.used = used
        alloc.pnl = pnl
        alloc.current_exposure = exposure
        alloc.available = max(Decimal("0"), alloc.allocated - used)

    def get_allocation(self, strategy_id: str) -> StrategyAllocation | None:
        return self.allocations.get(strategy_id)

    def get_total_allocated(self) -> Decimal:
        return sum(a.allocated for a in self.allocations.values())

    def get_total_exposure(self) -> Decimal:
        return sum(a.current_exposure for a in self.allocations.values())

    # ════════════════════════════════════════════════════════════════════════
    # ALLOCATION OPTIMIZATION
    # ════════════════════════════════════════════════════════════════════════

    def set_allocation_mode(self, mode: AllocationMode) -> None:
        self._allocation_mode = mode
        logger.info(f"Allocation mode set to {mode.value}")

    def optimize_allocation(
        self,
        strategies: list[Strategy],
        performance_data: dict[str, Any],
        correlation_matrix: dict[str, dict[str, Decimal]] | None = None,
        regime_exposure: dict[str, Decimal] | None = None,
    ) -> AllocationResult:
        """Optimize capital allocation across strategies."""

        if self._allocation_mode == AllocationMode.MANUAL:
            return AllocationResult(
                mode=AllocationMode.MANUAL,
                allocations={
                    s.strategy_id: self.allocations.get(s.strategy_id, StrategyAllocation(s.strategy_id)).allocated
                    for s in strategies
                },
                total_allocated=self.get_total_allocated(),
                cash_reserve=self.state.available_cash,
            )

        # Get strategy metrics
        metrics = {}
        for s in strategies:
            if s.strategy_id in performance_data:
                metrics[s.strategy_id] = performance_data[s.strategy_id]

        if not metrics:
            return AllocationResult(
                mode=self._allocation_mode,
                allocations={},
                total_allocated=Decimal("0"),
                cash_reserve=self.state.available_cash,
            )

        # Calculate allocations based on mode
        if self._allocation_mode == AllocationMode.EQUAL:
            allocations = self._equal_allocation(metrics)
        elif self._allocation_mode == AllocationMode.RISK_PARITY:
            allocations = self._risk_parity_allocation(metrics)
        elif self._allocation_mode == AllocationMode.SHARPE_WEIGHTED:
            allocations = self._sharpe_weighted_allocation(metrics)
        elif self._allocation_mode == AllocationMode.CORRELATION_AWARE:
            allocations = self._correlation_aware_allocation(metrics, correlation_matrix or {})
        elif self._allocation_mode == AllocationMode.VOLATILITY_TARGET:
            allocations = self._volatility_target_allocation(metrics)
        else:
            allocations = self._manual_allocation(metrics)

        # Apply constraints
        allocations = self._apply_constraints(allocations, correlation_matrix or {})

        total = sum(allocations.values())
        cash_reserve = max(Decimal("0"), self.state.total_capital - total)

        return AllocationResult(
            mode=self._allocation_mode,
            allocations=allocations,
            total_allocated=total,
            cash_reserve=cash_reserve,
            correlation_matrix=correlation_matrix or {},
        )

    def _equal_allocation(self, metrics: dict[str, Any]) -> dict[str, Decimal]:
        n = len(metrics)
        if n == 0:
            return {}
        per_strategy = self.state.total_capital / n * Decimal("0.8")  # Keep 20% cash
        return {sid: per_strategy for sid in metrics}

    def _risk_parity_allocation(self, metrics: dict[str, Any]) -> dict[str, Decimal]:
        """Allocate inversely proportional to volatility."""
        vols = {sid: m.get("volatility", Decimal("1")) for sid, m in metrics.items()}
        inv_vols = {sid: Decimal("1") / max(v, Decimal("0.01")) for sid, v in vols.items()}
        total_inv = sum(inv_vols.values())
        capital = self.state.total_capital * Decimal("0.8")
        return {sid: capital * inv / total_inv for sid, inv in inv_vols.items()}

    def _sharpe_weighted_allocation(self, metrics: dict[str, Any]) -> dict[str, Decimal]:
        sharpes = {sid: max(m.get("sharpe", Decimal("0")), Decimal("0")) for sid, m in metrics.items()}
        total_sharpe = sum(sharpes.values())
        if total_sharpe == 0:
            return self._equal_allocation(metrics)
        capital = self.state.total_capital * Decimal("0.8")
        return {sid: capital * s / total_sharpe for sid, s in sharpes.items()}

    def _correlation_aware_allocation(
        self,
        metrics: dict[str, Any],
        correlation_matrix: dict[str, dict[str, Decimal]],
    ) -> dict[str, Decimal]:
        """Allocate considering correlation to maximize diversification."""
        # Start with Sharpe-weighted, then reduce correlated pairs
        base = self._sharpe_weighted_allocation(metrics)

        if not correlation_matrix:
            return base

        # Reduce allocation for highly correlated strategies
        adjusted = base.copy()
        for sid1 in base:
            for sid2 in base:
                if sid1 != sid2:
                    corr = correlation_matrix.get(sid1, {}).get(sid2, Decimal("0"))
                    if corr > Decimal("0.7"):
                        # Reduce smaller allocation
                        if base[sid1] < base[sid2]:
                            adjusted[sid1] *= Decimal("0.7")
                        else:
                            adjusted[sid2] *= Decimal("0.7")

        return adjusted

    def _volatility_target_allocation(self, metrics: dict[str, Any]) -> dict[str, Decimal]:
        """Target fixed portfolio volatility."""
        target_vol = Decimal("0.15")  # 15% annual
        vols = {sid: max(m.get("volatility", Decimal("1")), Decimal("0.01")) for sid, m in metrics.items()}
        weights = {sid: target_vol / v for sid, v in vols.items()}
        total_w = sum(weights.values())
        capital = self.state.total_capital * Decimal("0.8")
        return {sid: capital * w / total_w for sid, w in weights.items()}

    def _manual_allocation(self, metrics: dict[str, Any]) -> dict[str, Decimal]:
        return {sid: self.allocations.get(sid, StrategyAllocation(sid)).allocated for sid in metrics}

    def _apply_constraints(
        self,
        allocations: dict[str, Decimal],
        correlation_matrix: dict[str, dict[str, Decimal]],
    ) -> dict[str, Decimal]:
        """Apply allocation constraints."""
        result = allocations.copy()
        total = sum(result.values())
        max_capital = self.state.total_capital * Decimal("0.8")

        # Cap total allocation
        if total > max_capital:
            scale = max_capital / total
            result = {sid: amt * scale for sid, amt in result.items()}

        # Max per strategy (20% of capital)
        max_per_strategy = self.state.total_capital * Decimal("0.2")
        for sid in result:
            if result[sid] > max_per_strategy:
                result[sid] = max_per_strategy

        return result

    def check_rebalance_needed(self) -> bool:
        """Check if rebalancing is needed."""
        current_alloc = self.get_current_allocation_pct()
        target_alloc = self.get_target_allocation_pct()
        drift = max(
            abs(current_alloc.get(sid, Decimal("0")) - target_alloc.get(sid, Decimal("0")))
            for sid in set(current_alloc) | set(target_alloc)
        )
        return drift > self._rebalance_threshold

    def get_current_allocation_pct(self) -> dict[str, Decimal]:
        total = self.get_total_allocated()
        if total == 0:
            return {}
        return {sid: alloc.allocated / total for sid, alloc in self.allocations.items()}

    def get_target_allocation_pct(self) -> dict[str, Decimal]:
        # This would come from the last optimization result
        return {}

    # ════════════════════════════════════════════════════════════════════════
    # STATE QUERIES
    # ═══════════════════════════════════════════════════════════════════════

    def get_state(self) -> CapitalState:
        return self.state

    def get_summary(self) -> dict[str, Any]:
        return {
            "total_capital": str(self.state.total_capital),
            "available_cash": str(self.state.available_cash),
            "invested_capital": str(self.state.invested_capital),
            "equity": str(self.state.equity),
            "realized_pnl": str(self.state.realized_pnl),
            "unrealized_pnl": str(self.state.unrealized_pnl),
            "current_drawdown": str(self.state.current_drawdown),
            "max_drawdown": str(self.state.max_drawdown),
            "total_exposure": str(self.get_total_exposure()),
            "leverage": str(self.state.leverage),
            "num_strategies": len(self.allocations),
            "allocation_mode": self._allocation_mode.value,
        }

    def _recalculate_equity(self) -> None:
        self.state.equity = (
            self.state.available_cash + self.state.invested_capital + self.state.unrealized_pnl - self.state.margin_used
        )
        self.state.portfolio_value = self.state.equity
        if self.state.equity > 0:
            self.state.leverage = self.get_total_exposure() / self.state.equity
            self.state.current_drawdown = max(
                Decimal("0"),
                (self.state.max_drawdown - self.state.equity) / self.state.max_drawdown
                if self.state.max_drawdown > 0
                else Decimal("0"),
            )


# ═════════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════════

_capital_engine: CapitalEngine | None = None


def get_capital_engine(initial_capital: Decimal = Decimal("0")) -> CapitalEngine:
    global _capital_engine
    if _capital_engine is None:
        _capital_engine = CapitalEngine(initial_capital)
    return _capital_engine
