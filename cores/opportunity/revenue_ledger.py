"""Revenue Ledger — Follow complete lifecycle of earnings.

Maps the execution queue state machine to revenue states:
DISCOVERED → CLAIMED → CLAIM_CONFIRMED → WORK_STARTED → WORK_COMPLETED →
PAYMENT_REQUESTED → PAYMENT_CONFIRMED → EARNED → PAID → NET

This is the canonical revenue tracking for OWNEX, ensuring the Revenue Rule:
no feature enters the roadmap unless it increases vulnerability detection,
evidence quality, acceptance probability, or system learning.
"""

from __future__ import annotations

from core.execution_queue.models import ExecState, ExecutionQueueStore
from cores.availability import compute_availability_score, evaluate_availability, is_available

# ── Revenue States (extended from ExecState) ────────────────────────────────

REVENUE_STATES = [
    "discovered",  # Opportunity discovered, no action yet
    "claimed",  # Executor has claimed the opportunity
    "confirmed_claim",  # Claim validated, ready to work
    "work_started",  # Execution has begun
    "work_completed",  # Execution finished, ready for verification
    "payment_requested",  # Payment being processed
    "payment_confirmed",  # Payment validated
    "earned",  # Earnings confirmed (verified)
    "paid",  # Payment received
    "net",  # Net earnings after fees/cuts
]

# Mapping from ExecState to Revenue State
EXEC_TO_REVENUE: dict[ExecState, str] = {
    ExecState.DISCOVERED: "discovered",
    ExecState.QUALIFIED: "claimed",
    ExecState.READY: "confirmed_claim",
    ExecState.EXECUTING: "work_started",
    ExecState.WAITING_HUMAN: "work_completed",
    ExecState.SUBMITTED: "payment_requested",
    ExecState.VERIFICATION: "payment_confirmed",
    ExecState.PAID: "earned",
    ExecState.REJECTED: "net",  # or "rejected" depending on policy
    ExecState.FAILED: "net",  # or "rejected" depending on policy
    ExecState.DEAD_LETTER: "net",
}

# Reverse mapping
REVENUE_TO_EXEC: dict[str, ExecState] = {v: k for k, v in EXEC_TO_REVENUE.items()}

# Terminal revenue states
TERMINAL_REVENUE: set[str] = {"net", "rejected"}  # depends on policy


# ── Revenue Ledger Store ────────────────────────────────────────────────────


class RevenueLedger:
    """Ledger that tracks revenue lifecycle per execution item."""

    def __init__(self, store: ExecutionQueueStore | None = None):
        self._store = store or ExecutionQueueStore()
        self._revenue_states: dict[str, str] = {}  # item_id -> revenue_state

    def _get_revenue_state(self, item_id: str) -> str:
        """Get current revenue state for an item."""
        # Try to get from store's history/state
        item = self._store.get(item_id)
        if not item:
            return "discovered"

        exec_state = ExecState(item["state"])
        return EXEC_TO_REVENUE.get(exec_state, "discovered")

    def _set_revenue_state(self, item_id: str, revenue_state: str) -> None:
        """Set revenue state for an item."""
        if revenue_state not in REVENUE_STATES:
            raise ValueError(f"Invalid revenue state: {revenue_state}")
        self._revenue_states[item_id] = revenue_state

    def add(self, item_id: str, payload: dict | None = None) -> dict:
        """Add new item to queue and initialize revenue tracking."""
        # Add to execution queue
        exec_item = self._store.add(item_id, payload)

        # Initialize revenue state
        self._set_revenue_state(item_id, "discovered")

        return exec_item

    def transition(self, item_id: str, target_exec_state: ExecState) -> dict:
        """Transition execution queue item and update revenue state."""
        # Transition in execution queue
        exec_item = self._store.transition(item_id, target_exec_state.value)

        # Update revenue state
        old_revenue = self._get_revenue_state(item_id)
        new_revenue = EXEC_TO_REVENUE.get(target_exec_state, "discovered")

        # Only transition if revenue state changes (or apply business rules)
        if old_revenue != new_revenue:
            self._revenue_states[item_id] = new_revenue

            # Emit transition events for business logic
            # Could integrate with event system here

        return {
            "item_id": item_id,
            "exec_state": exec_item["state"],
            "revenue_state": self._get_revenue_state(item_id),
            "old_revenue_state": old_revenue,
            "new_revenue_state": new_revenue,
            "history": exec_item.get("history", []),
        }

    def get_revenue_state(self, item_id: str) -> dict:
        """Get current revenue state and execution state for an item."""
        exec_item = self._store.get(item_id)
        if not exec_item:
            return {"revenue_state": "discovered", "exec_state": None}

        return {
            "revenue_state": self._get_revenue_state(item_id),
            "exec_state": exec_item["state"],
            "history": exec_item.get("history", []),
            "payload": exec_item.get("payload", {}),
        }

    def pending_by_revenue(self, *revenue_states: str) -> list[str]:
        """Get items pending by revenue state."""
        items: list[str] = []
        for item_id in self._revenue_states:
            if self._revenue_states[item_id] in revenue_states:
                items.append(item_id)
        return items

    def get_earnings_summary(self) -> dict:
        """Get summary of earnings across all tracked items."""
        total_items = len(self._revenue_states)
        if total_items == 0:
            return {"total": 0, "by_state": {}}

        by_state: dict[str, int] = {}
        for _, revenue_state in self._revenue_states.items():
            by_state[revenue_state] = by_state.get(revenue_state, 0) + 1

        return {
            "total": total_items,
            "by_state": by_state,
            "terminal": sum(1 for s in self._revenue_states.values() if s in TERMINAL_REVENUE),
        }


# Singleton instance
revenue_ledger = RevenueLedger()


# Convenience functions
def add_opportunity(item_id: str, payload: dict | None = None) -> dict:
    """Add new opportunity to ledger."""
    return revenue_ledger.add(item_id, payload)


def transition_revenue(item_id: str, target_exec_state: ExecState) -> dict:
    """Transition revenue ledger for an item."""
    return revenue_ledger.transition(item_id, target_exec_state)


def get_revenue_state(item_id: str) -> dict:
    """Get revenue state for an item."""
    return revenue_ledger.get_revenue_state(item_id)


def get_earnings_summary() -> dict:
    """Get earnings summary."""
    return revenue_ledger.get_earnings_summary()


# Export all public symbols
__all__ = [
    "REVENUE_STATES",
    "EXEC_TO_REVENUE",
    "REVENUE_TO_EXEC",
    "TERMINAL_REVENUE",
    "RevenueLedger",
    "revenue_ledger",
    "add_opportunity",
    "transition_revenue",
    "get_revenue_state",
    "get_earnings_summary",
    "compute_availability_score",  # reuse from availability
    "evaluate_availability",
    "is_available",
]
