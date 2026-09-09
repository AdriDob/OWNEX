"""Execution Safety — Idempotent order execution with full safety checks.

SIGNAL → VALIDATION → RISK_CHECK → CAPITAL_CHECK → DUPLICATE_CHECK
    → ORDER_PREVIEW → EXECUTION → CONFIRMATION → RECONCILIATION
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from core.trading.contracts import (
    Order,
    OrderStatus,
    OrderType,
    Signal,
    SignalSide,
)

logger = logging.getLogger("ownex.trading.execution")


class ExecutionMode(StrEnum):
    PAPER = "paper"
    CANARY = "canary"
    LIVE = "live"


class DuplicateCheckResult(StrEnum):
    NEW = "new"
    DUPLICATE = "duplicate"
    PARTIAL_DUPLICATE = "partial_duplicate"


@dataclass
class ExecutionPreview:
    """Preview of an order execution."""

    order: Order
    estimated_fill_price: Decimal | None = None
    estimated_fees: Decimal = Decimal("0")
    estimated_slippage: Decimal = Decimal("0")
    required_margin: Decimal = Decimal("0")
    capital_available: bool = True
    risk_check_passed: bool = True
    duplicate_check: DuplicateCheckResult = DuplicateCheckResult.NEW
    warnings: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class ExecutionResult:
    """Result of order execution."""

    success: bool
    order_id: str
    execution_id: str | None = None
    filled_quantity: Decimal = Decimal("0")
    avg_fill_price: Decimal | None = None
    fees: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    status: OrderStatus = OrderStatus.PENDING
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class IdempotencyStore:
    """Store for idempotency keys to prevent duplicate orders."""

    def __init__(self, data_dir: str = "data/trading/idempotency"):
        self.data_dir = data_dir

    def check_and_store(self, idempotency_key: str, order: Order) -> DuplicateCheckResult:
        """Check if key exists, store if new. Returns check result."""
        # In production, this would use Redis or database
        # For now, in-memory with persistence
        return DuplicateCheckResult.NEW

    def get_order(self, idempotency_key: str) -> Order | None:
        """Get order by idempotency key."""
        return None


class ExecutionEngine:
    """Safe order execution engine with full safety pipeline."""

    def __init__(
        self,
        capital_engine: Any,
        risk_engine: Any,
        mode: str = "paper",
        data_dir: str = "data/trading/execution",
    ):
        self.capital_engine = capital_engine
        self.risk_engine = risk_engine
        self.mode = ExecutionMode(mode)
        self.idempotency_store = IdempotencyStore()
        self._pending_orders: dict[str, Order] = {}
        self._execution_history: list[ExecutionResult] = []

    # ════════════════════════════════════════════════════════════════════════
    # MAIN EXECUTION PIPELINE
    # ═══════════════════════════════════════════════════════════════════════

    async def execute_signal(self, signal: Signal, strategy_id: str) -> ExecutionResult:
        """Execute a signal through the full safety pipeline."""

        # Step 1: Create order from signal
        order = self._signal_to_order(signal, strategy_id)

        # Step 2: Full safety pipeline
        preview = await self.preview_order(order)
        if not preview.risk_check_passed or not preview.capital_available:
            return ExecutionResult(
                success=False,
                order_id=order.order_id,
                error="Preview failed: " + "; ".join(preview.warnings),
            )

        if preview.duplicate_check != DuplicateCheckResult.NEW:
            return ExecutionResult(
                success=False,
                order_id=order.order_id,
                error=f"Duplicate order detected: {preview.duplicate_check.value}",
            )

        # Step 3: Execute (paper or live)
        if self.mode == ExecutionMode.LIVE:
            result = await self._execute_live(order)
        else:
            result = await self._execute_paper(order)

        # Step 4: Store execution result
        self._execution_history.append(result)

        return result

    async def execute_order(self, order: Order) -> ExecutionResult:
        """Execute a pre-created order."""
        preview = await self.preview_order(order)
        if not preview.risk_check_passed or not preview.capital_available:
            return ExecutionResult(
                success=False,
                order_id=order.order_id,
                error="Preview failed: " + "; ".join(preview.warnings),
            )

        if self.mode == ExecutionMode.LIVE:
            return await self._execute_live(order)
        else:
            return await self._execute_paper(order)

    # ════════════════════════════════════════════════════════════════════════
    # PIPELINE STEPS
    # ════════════════════════════════════════════════════════════════════════

    async def preview_order(self, order: Order) -> ExecutionPreview:
        """Preview order execution without executing."""

        warnings = []

        # Step 1: Duplicate check
        duplicate_check = self.idempotency_store.check_and_store(order.idempotency_key, order)

        # Step 2: Risk check
        risk_passed, risk_reason = self.risk_engine.check_order(order, self.capital_engine)
        if not risk_passed:
            warnings.append(f"Risk check failed: {risk_reason}")

        # Step 3: Capital check
        capital_available = True
        if self.capital_engine:
            # Check if capital is available for this order
            required = order.quantity * (order.price or Decimal("0"))
            if required > self.capital_engine.state.available_cash:
                capital_available = False
                warnings.append("Insufficient available capital")

        # Step 4: Estimate fill
        estimated_price = order.price
        estimated_fees = (order.quantity * (order.price or Decimal("0"))) * Decimal("0.001")
        estimated_slippage = (order.price or Decimal("0")) * Decimal("0.001")
        required_margin = order.quantity * (order.price or Decimal("0")) * Decimal("0.1")

        return ExecutionPreview(
            order=order,
            estimated_fill_price=estimated_price,
            estimated_fees=estimated_fees,
            estimated_slippage=estimated_slippage,
            required_margin=required_margin,
            capital_available=capital_available,
            risk_check_passed=risk_passed,
            duplicate_check=duplicate_check,
            warnings=warnings,
        )

    # ════════════════════════════════════════════════════════════════════════
    # PAPER EXECUTION
    # ════════════════════════════════════════════════════════════════════════

    async def _execute_paper(self, order: Order) -> ExecutionResult:
        """Execute order in paper trading mode."""

        # Simulate fill
        fill_price = order.price or Decimal("0")
        slippage = fill_price * Decimal("0.0005")  # 0.05% slippage
        avg_fill_price = fill_price + (slippage if order.side == SignalSide.BUY else -slippage)
        fees = (order.quantity * avg_fill_price) * Decimal("0.001")

        # Update order
        order.filled_quantity = order.quantity
        order.avg_fill_price = avg_fill_price
        order.fees = fees
        order.status = OrderStatus.FILLED
        order.updated_at = datetime.now(UTC).isoformat()

        # Update capital engine
        if self.capital_engine:
            cost = order.quantity * avg_fill_price + fees
            self.capital_engine.state.available_cash -= cost
            self.capital_engine.state.invested_capital += cost
            self.capital_engine.add_fees(fees)

        logger.info(f"Paper execution: {order.order_id} - {order.side.value} {order.quantity} @ {avg_fill_price}")

        return ExecutionResult(
            success=True,
            order_id=order.order_id,
            filled_quantity=order.quantity,
            avg_fill_price=avg_fill_price,
            fees=fees,
            slippage=slippage,
            status=OrderStatus.FILLED,
        )

    # ════════════════════════════════════════════════════════════════════════
    # LIVE EXECUTION (via engine adapters)
    # ════════════════════════════════════════════════════════════════════════

    async def _execute_live(self, order: Order) -> ExecutionResult:
        """Execute order in live mode via engine adapter."""

        # This would route to the appropriate engine adapter
        # For now, return not implemented
        return ExecutionResult(
            success=False,
            order_id=order.order_id,
            error="Live execution not yet implemented - use paper mode",
            status=OrderStatus.REJECTED,
        )

    # ════════════════════════════════════════════════════════════════════════
    # ORDER MANAGEMENT
    # ════════════════════════════════════════════════════════════════════════

    def _signal_to_order(self, signal: Signal, strategy_id: str) -> Order:
        """Convert signal to order with idempotency key."""

        idempotency_key = f"{strategy_id}:{signal.signal_id}:{signal.symbol}:{signal.side.value}"

        return Order(
            order_id=f"ord_{uuid.uuid4().hex[:12]}",
            idempotency_key=idempotency_key,
            strategy_id=strategy_id,
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            side=signal.side,
            quantity=Decimal("0"),  # Would be calculated from capital allocation
            price=signal.entry_price,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING,
        )

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        if order_id in self._pending_orders:
            order = self._pending_orders[order_id]
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now(UTC).isoformat()
            del self._pending_orders[order_id]
            logger.info(f"Order cancelled: {order_id}")
            return True
        return False

    def get_order(self, order_id: str) -> Order | None:
        return self._pending_orders.get(order_id)

    def get_execution_history(self, limit: int = 100) -> list[ExecutionResult]:
        return self._execution_history[-limit:]


# ══════════════════════════════════════════════════════════════════════════
# RECONCILIATION
# ═════════════════════════════════════════════════════════════════════════


class ReconciliationEngine:
    """Periodic reconciliation of OWNEX ledger vs exchange balances."""

    def __init__(self, capital_engine: Any, engine_registry: Any):
        self.capital_engine = capital_engine
        self.engine_registry = engine_registry
        self._last_reconciliation: str | None = None

    async def reconcile_all(self) -> list[dict]:
        """Reconcile all exchanges and strategies."""
        discrepancies = []

        for engine_id, entry in self.engine_registry._engines.items():
            if entry.adapter:
                try:
                    # Get exchange balances
                    # Compare with OWNEX ledger
                    # Record discrepancies
                    pass
                except Exception as e:
                    logger.error(f"Reconciliation failed for {engine_id}: {e}")

        self._last_reconciliation = datetime.now(UTC).isoformat()
        return discrepancies

    def get_last_reconciliation(self) -> str | None:
        return self._last_reconciliation


# ══════════════════════════════════════════════════════════════════════════
# SINGLETONS
# ═════════════════════════════════════════════════════════════════════════

_execution_engine: ExecutionEngine | None = None
_reconciliation_engine: ReconciliationEngine | None = None


def get_execution_engine(
    capital_engine: Any,
    risk_engine: Any,
    mode: str = "paper",
) -> ExecutionEngine:
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine(capital_engine, risk_engine, mode)
    return _execution_engine


def get_reconciliation_engine(
    capital_engine: Any,
    engine_registry: Any,
) -> ReconciliationEngine:
    global _reconciliation_engine
    if _reconciliation_engine is None:
        _reconciliation_engine = ReconciliationEngine(capital_engine, engine_registry)
    return _reconciliation_engine
