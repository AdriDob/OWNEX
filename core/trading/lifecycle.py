"""Strategy Lifecycle State Machine — Canonical state transitions for strategies.

DISCOVERED → INSTALLED → BACKTESTING → BACKTEST_FAILED
    ↓                              ↓
    ↓                        VALIDATING → VALIDATED
    ↓                              ↓
    ↓                        PAPER → CANARY → LIVE
    ↓                              ↓
    ↓                        PAUSED → RETIRED
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from core.trading.contracts import (
    Strategy,
    StrategyStatus,
)

logger = logging.getLogger("ownex.trading.lifecycle")


# ═════════════════════════════════════════════════════════════════════════
# STATE MACHINE
# ════════════════════════════════════════════════════════════════════════

# Valid transitions: current_state -> set of allowed next_states
TRANSITIONS: dict[StrategyStatus, set[StrategyStatus]] = {
    StrategyStatus.DISCOVERED: {StrategyStatus.INSTALLED, StrategyStatus.RETIRED},
    StrategyStatus.INSTALLED: {StrategyStatus.BACKTESTING, StrategyStatus.DISCOVERED, StrategyStatus.RETIRED},
    StrategyStatus.BACKTESTING: {StrategyStatus.BACKTEST_FAILED, StrategyStatus.VALIDATING, StrategyStatus.RETIRED},
    StrategyStatus.BACKTEST_FAILED: {StrategyStatus.INSTALLED, StrategyStatus.RETIRED},
    StrategyStatus.VALIDATING: {StrategyStatus.VALIDATED, StrategyStatus.BACKTEST_FAILED, StrategyStatus.RETIRED},
    StrategyStatus.VALIDATED: {StrategyStatus.PAPER, StrategyStatus.RETIRED},
    StrategyStatus.PAPER: {StrategyStatus.CANARY, StrategyStatus.VALIDATED, StrategyStatus.RETIRED},
    StrategyStatus.CANARY: {StrategyStatus.LIVE, StrategyStatus.PAPER, StrategyStatus.RETIRED},
    StrategyStatus.LIVE: {StrategyStatus.PAUSED, StrategyStatus.RETIRED},
    StrategyStatus.PAUSED: {StrategyStatus.LIVE, StrategyStatus.RETIRED},
    StrategyStatus.RETIRED: {StrategyStatus.DISCOVERED},  # Can restart from scratch
}

# Terminal states (no forward progress without explicit action)
TERMINAL_STATES = {StrategyStatus.RETIRED, StrategyStatus.BACKTEST_FAILED}

# States that require human approval to enter
APPROVAL_REQUIRED = {
    StrategyStatus.LIVE,
    StrategyStatus.CANARY,
}


@dataclass
class TransitionEvent:
    """Record of a state transition."""

    strategy_id: str
    from_state: StrategyStatus
    to_state: StrategyStatus
    trigger: str  # "automatic", "human", "validation_passed", "validation_failed", "risk_breach", "manual"
    reason: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict = field(default_factory=dict)


class StrategyLifecycleManager:
    """Manages strategy lifecycle state transitions."""

    def __init__(self):
        self._transition_history: dict[str, list[TransitionEvent]] = {}

    # ════════════════════════════════════════════════════════════════════════
    # CORE TRANSITION LOGIC
    # ═══════════════════════════════════════════════════════════════════════

    def can_transition(self, current: StrategyStatus, target: StrategyStatus) -> bool:
        """Check if a transition is valid."""
        return target in TRANSITIONS.get(current, set())

    def transition(
        self,
        strategy: Strategy,
        target_state: StrategyStatus,
        trigger: str = "manual",
        reason: str = "",
        metadata: dict | None = None,
    ) -> bool:
        """Execute a state transition with validation."""

        if not self.can_transition(strategy.status, target_state):
            logger.warning(
                f"Invalid transition for strategy {strategy.strategy_id}: "
                f"{strategy.status.value} -> {target_state.value}"
            )
            return False

        # Check approval requirements
        if target_state in APPROVAL_REQUIRED and trigger != "human":
            logger.warning(f"Transition to {target_state.value} requires human approval")
            return False

        # Execute transition
        old_state = strategy.status
        strategy.status = target_state
        strategy.updated_at = datetime.now(UTC).isoformat()

        # Record transition
        event = TransitionEvent(
            strategy_id=strategy.strategy_id,
            from_state=old_state,
            to_state=target_state,
            trigger=trigger,
            reason=reason,
            metadata=metadata or {},
        )

        if strategy.strategy_id not in self._transition_history:
            self._transition_history[strategy.strategy_id] = []
        self._transition_history[strategy.strategy_id].append(event)

        logger.info(f"Strategy {strategy.strategy_id}: {old_state.value} -> {target_state.value} ({trigger})")
        return True

    # ════════════════════════════════════════════════════════════════════════
    # HIGH-LEVEL OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def start_installation(self, strategy: Strategy) -> bool:
        """Start engine installation for a discovered strategy."""
        return self.transition(
            strategy, StrategyStatus.INSTALLED, trigger="automatic", reason="Engine installation started"
        )

    def complete_installation(self, strategy: Strategy, success: bool) -> bool:
        """Complete engine installation."""
        if success:
            return self.transition(
                strategy,
                StrategyStatus.BACKTESTING,
                trigger="automatic",
                reason="Installation complete, starting backtest",
            )
        else:
            return self.transition(
                strategy, StrategyStatus.DISCOVERED, trigger="automatic", reason="Installation failed"
            )

    def start_backtest(self, strategy: Strategy) -> bool:
        """Start backtesting phase."""
        return self.transition(strategy, StrategyStatus.BACKTESTING, trigger="automatic", reason="Backtest started")

    def complete_backtest(self, strategy: Strategy, success: bool) -> bool:
        """Complete backtesting phase."""
        if success:
            return self.transition(
                strategy,
                StrategyStatus.VALIDATING,
                trigger="validation_passed",
                reason="Backtest passed, starting validation",
            )
        else:
            return self.transition(
                strategy, StrategyStatus.BACKTEST_FAILED, trigger="validation_failed", reason="Backtest failed"
            )

    def start_validation(self, strategy: Strategy) -> bool:
        """Start validation pipeline."""
        return self.transition(
            strategy, StrategyStatus.VALIDATING, trigger="automatic", reason="Validation pipeline started"
        )

    def complete_validation(self, strategy: Strategy, passed: bool) -> bool:
        """Complete validation pipeline."""
        if passed:
            return self.transition(
                strategy, StrategyStatus.VALIDATED, trigger="validation_passed", reason="All validation phases passed"
            )
        else:
            return self.transition(
                strategy,
                StrategyStatus.BACKTEST_FAILED,
                trigger="validation_failed",
                reason="Validation pipeline failed",
            )

    def start_paper_trading(self, strategy: Strategy) -> bool:
        """Start paper trading."""
        return self.transition(strategy, StrategyStatus.PAPER, trigger="human", reason="Starting paper trading")

    def complete_paper_trading(self, strategy: Strategy, success: bool) -> bool:
        """Complete paper trading."""
        if success:
            return self.transition(
                strategy,
                StrategyStatus.CANARY,
                trigger="automatic",
                reason="Paper trading successful, eligible for canary",
            )
        else:
            return self.transition(
                strategy,
                StrategyStatus.VALIDATED,
                trigger="automatic",
                reason="Paper trading failed, returning to validated",
            )

    def start_canary(self, strategy: Strategy, human_approved: bool = True) -> bool:
        """Start canary deployment (requires human approval)."""
        trigger = "human" if human_approved else "automatic"
        return self.transition(strategy, StrategyStatus.CANARY, trigger=trigger, reason="Canary deployment approved")

    def start_live(self, strategy: Strategy, human_approved: bool = True) -> bool:
        """Start live trading (requires human approval)."""
        trigger = "human" if human_approved else "automatic"
        return self.transition(strategy, StrategyStatus.LIVE, trigger=trigger, reason="Live trading approved")

    def pause_strategy(self, strategy: Strategy, reason: str = "Manual pause") -> bool:
        """Pause a live strategy."""
        return self.transition(strategy, StrategyStatus.PAUSED, trigger="human", reason=reason)

    def resume_strategy(self, strategy: Strategy, human_approved: bool = True) -> bool:
        """Resume a paused strategy."""
        trigger = "human" if human_approved else "automatic"
        return self.transition(strategy, StrategyStatus.LIVE, trigger=trigger, reason="Strategy resumed")

    def retire_strategy(self, strategy: Strategy, reason: str = "Strategy retired") -> bool:
        """Retire a strategy."""
        return self.transition(strategy, StrategyStatus.RETIRED, trigger="human", reason=reason)

    def restart_strategy(self, strategy: Strategy) -> bool:
        """Restart a retired strategy from discovered state."""
        return self.transition(strategy, StrategyStatus.DISCOVERED, trigger="human", reason="Strategy restarted")

    # ════════════════════════════════════════════════════════════════════════
    # QUERIES
    # ═══════════════════════════════════════════════════════════════════════

    def get_valid_transitions(self, current_state: StrategyStatus) -> set[StrategyStatus]:
        """Get all valid next states from current state."""
        return TRANSITIONS.get(current_state, set())

    def is_terminal(self, state: StrategyStatus) -> bool:
        """Check if state is terminal."""
        return state in TERMINAL_STATES

    def requires_approval(self, target_state: StrategyStatus) -> bool:
        """Check if target state requires human approval."""
        return target_state in APPROVAL_REQUIRED

    def get_transition_history(self, strategy_id: str) -> list[dict]:
        """Get transition history for a strategy."""
        return [event.__dict__ for event in self._transition_history.get(strategy_id, [])]

    def can_enter_live(self, strategy: Strategy) -> tuple[bool, str]:
        """Check if strategy can enter live trading."""
        if strategy.status != StrategyStatus.CANARY:
            return False, "Strategy must be in CANARY state"

        # Additional checks would go here (risk limits, capital availability, etc.)
        return True, "Eligible for live trading"


# ═════════════════════════════════════════════════════════════════════════
# STRATEGY REGISTRY (persistent storage for strategy definitions)
# ════════════════════════════════════════════════════════════════════════


@dataclass
class StrategyRecord:
    """Persistent strategy record with lifecycle info."""

    strategy: Strategy
    lifecycle_manager: StrategyLifecycleManager = field(default_factory=StrategyLifecycleManager)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def transition(self, target_state: StrategyStatus, **kwargs) -> bool:
        return self.lifecycle_manager.transition(self.strategy, target_state, **kwargs)


class StrategyRegistry:
    """Registry for all strategies with lifecycle management."""

    def __init__(self):
        self._strategies: dict[str, StrategyRecord] = {}

    def register_strategy(self, strategy: Strategy) -> bool:
        """Register a new strategy."""
        if strategy.strategy_id in self._strategies:
            logger.warning(f"Strategy {strategy.strategy_id} already registered")
            return False
        self._strategies[strategy.strategy_id] = StrategyRecord(strategy=strategy)
        return True

    def get_strategy(self, strategy_id: str) -> Strategy | None:
        record = self._strategies.get(strategy_id)
        return record.strategy if record else None

    def get_record(self, strategy_id: str) -> StrategyRecord | None:
        return self._strategies.get(strategy_id)

    def list_strategies(self, status: StrategyStatus | None = None) -> list[Strategy]:
        strategies = [r.strategy for r in self._strategies.values()]
        if status:
            strategies = [s for s in strategies if s.status == status]
        return strategies

    def transition_strategy(self, strategy_id: str, target_state: StrategyStatus, **kwargs) -> bool:
        record = self._strategies.get(strategy_id)
        if not record:
            return False
        return record.transition(target_state, **kwargs)

    def get_lifecycle_status(self, strategy_id: str) -> dict | None:
        record = self._strategies.get(strategy_id)
        if not record:
            return None

        return {
            "strategy_id": strategy_id,
            "current_state": record.strategy.status.value,
            "valid_transitions": [
                s.value for s in record.lifecycle_manager.get_valid_transitions(record.strategy.status)
            ],
            "requires_approval_for_live": record.lifecycle_manager.requires_approval(StrategyStatus.LIVE),
            "can_enter_live": record.lifecycle_manager.can_enter_live(record.strategy),
            "transition_history": record.lifecycle_manager.get_transition_history(strategy_id),
            "is_terminal": record.lifecycle_manager.is_terminal(record.strategy.status),
        }


# ═════════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════════

_strategy_registry: StrategyRegistry | None = None


def get_strategy_registry() -> StrategyRegistry:
    """Get the global strategy registry singleton."""
    global _strategy_registry
    if _strategy_registry is None:
        _strategy_registry = StrategyRegistry()
    return _strategy_registry


def get_lifecycle_manager() -> StrategyLifecycleManager:
    """Get a new lifecycle manager instance."""
    return StrategyLifecycleManager()


# ── Module-Level Wrappers for Scheduler Handlers ──────────────────────
# The trading jobs reference handlers like "core.trading.lifecycle:start_backtest"
# These need to be callable at module level for _resolve_handler to work.


def _get_lcm() -> StrategyLifecycleManager:
    """Get a StrategyLifecycleManager instance."""
    from core.trading.lifecycle import get_lifecycle_manager

    return get_lifecycle_manager()


def start_backtest_handler(strategy) -> bool:
    """Wrapper for start_backtest scheduler job."""
    lcm = _get_lcm()
    return lcm.start_backtest(strategy)


def complete_backtest_handler(strategy, success) -> bool:
    """Wrapper for complete_backtest scheduler job."""
    lcm = _get_lcm()
    return lcm.complete_backtest(strategy, success)


def start_validation_handler(strategy) -> bool:
    """Wrapper for start_validation scheduler job."""
    lcm = _get_lcm()
    return lcm.start_validation(strategy)


def complete_validation_handler(strategy, passed) -> bool:
    """Wrapper for complete_validation scheduler job."""
    lcm = _get_lcm()
    return lcm.complete_validation(strategy, passed)


def start_paper_trading_handler(strategy) -> bool:
    """Wrapper for start_paper_trading scheduler job."""
    lcm = _get_lcm()
    return lcm.start_paper_trading(strategy)


def complete_paper_trading_handler(strategy, success) -> bool:
    """Wrapper for complete_paper_trading scheduler job."""
    lcm = _get_lcm()
    return lcm.complete_paper_trading(strategy, success)


def start_canary_handler(strategy, human_approved=True) -> bool:
    """Wrapper for start_canary scheduler job."""
    lcm = _get_lcm()
    return lcm.start_canary(strategy, human_approved)


def start_live_handler(strategy, human_approved=True) -> bool:
    """Wrapper for start_live scheduler job."""
    lcm = _get_lcm()
    return lcm.start_live(strategy, human_approved)


def pause_strategy_handler(strategy, reason="Manual pause") -> bool:
    """Wrapper for pause_strategy scheduler job."""
    lcm = _get_lcm()
    return lcm.pause_strategy(strategy, reason)


def resume_strategy_handler(strategy, human_approved=True) -> bool:
    """Wrapper for resume_strategy scheduler job."""
    lcm = _get_lcm()
    return lcm.resume_strategy(strategy, human_approved)


def retire_strategy_handler(strategy, reason="Strategy retired") -> bool:
    """Wrapper for retire_strategy scheduler job."""
    lcm = _get_lcm()
    return lcm.retire_strategy(strategy, reason)


def restart_strategy_handler(strategy) -> bool:
    """Wrapper for restart_strategy scheduler job."""
    lcm = _get_lcm()
    return lcm.restart_strategy(strategy)


# Expose as module-level names for handler resolution
start_backtest = start_backtest_handler
complete_backtest = complete_backtest_handler
start_validation = start_validation_handler
complete_validation = complete_validation_handler
start_paper_trading = start_paper_trading_handler
complete_paper_trading = complete_paper_trading_handler
start_canary = start_canary_handler
start_live = start_live_handler
pause_strategy = pause_strategy_handler
resume_strategy = resume_strategy_handler
retire_strategy = retire_strategy_handler
restart_strategy = restart_strategy_handler


# ── Module-Level Wrappers for Scheduler Handlers ──────────────────────
# The trading jobs reference handlers like "core.trading.lifecycle:start_backtest"
# These need to be callable at module level for _resolve_handler to work.


def _get_lcm() -> StrategyLifecycleManager:
    """Get a StrategyLifecycleManager instance."""
    from core.trading.lifecycle import StrategyLifecycleManager

    return StrategyLifecycleManager()


def start_backtest_handler(strategy) -> bool:
    """Wrapper for start_backtest scheduler job."""
    lcm = _get_lcm()
    return lcm.start_backtest(strategy)


def complete_backtest_handler(strategy, success) -> bool:
    """Wrapper for complete_backtest scheduler job."""
    lcm = _get_lcm()
    return lcm.complete_backtest(strategy, success)


def start_validation_handler(strategy) -> bool:
    """Wrapper for start_validation scheduler job."""
    lcm = _get_lcm()
    return lcm.start_validation(strategy)


def complete_validation_handler(strategy, passed) -> bool:
    """Wrapper for complete_validation scheduler job."""
    lcm = _get_lcm()
    return lcm.complete_validation(strategy, passed)


def start_paper_trading_handler(strategy) -> bool:
    """Wrapper for start_paper_trading scheduler job."""
    lcm = _get_lcm()
    return lcm.start_paper_trading(strategy)


def complete_paper_trading_handler(strategy, success) -> bool:
    """Wrapper for complete_paper_trading scheduler job."""
    lcm = _get_lcm()
    return lcm.complete_paper_trading(strategy, success)


def start_canary_handler(strategy, human_approved=True) -> bool:
    """Wrapper for start_canary scheduler job."""
    lcm = _get_lcm()
    return lcm.start_canary(strategy, human_approved)


def start_live_handler(strategy, human_approved=True) -> bool:
    """Wrapper for start_live scheduler job."""
    lcm = _get_lcm()
    return lcm.start_live(strategy, human_approved)


def pause_strategy_handler(strategy, reason="Manual pause") -> bool:
    """Wrapper for pause_strategy scheduler job."""
    lcm = _get_lcm()
    return lcm.pause_strategy(strategy, reason)


def resume_strategy_handler(strategy, human_approved=True) -> bool:
    """Wrapper for resume_strategy scheduler job."""
    lcm = _get_lcm()
    return lcm.resume_strategy(strategy, human_approved)


def retire_strategy_handler(strategy, reason="Strategy retired") -> bool:
    """Wrapper for retire_strategy scheduler job."""
    lcm = _get_lcm()
    return lcm.retire_strategy(strategy, reason)


def restart_strategy_handler(strategy) -> bool:
    """Wrapper for restart_strategy scheduler job."""
    lcm = _get_lcm()
    return lcm.restart_strategy(strategy)


# Expose as module-level names for handler resolution
start_backtest = start_backtest_handler
complete_backtest = complete_backtest_handler
start_validation = start_validation_handler
complete_validation = complete_validation_handler
start_paper_trading = start_paper_trading_handler
complete_paper_trading = complete_paper_trading_handler
start_canary = start_canary_handler
start_live = start_live_handler
pause_strategy = pause_strategy_handler
resume_strategy = resume_strategy_handler
retire_strategy = retire_strategy_handler
restart_strategy = restart_strategy_handler
