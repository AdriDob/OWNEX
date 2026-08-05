"""Automatic Triggers System — Implements progression and safety triggers.

Automatically executes actions based on conditions:
- Progress to next phase when criteria met
- Downgrade when risks exceed limits
- Emergency stops on critical conditions
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum

from cores.financial_intelligence.progressive_scaling import (
    ProgressiveScalingManager,
    ScalingPhase,
    get_progressive_scaling_manager,
)
from cores.financial_intelligence.risk_monitor import (
    RiskLevel,
    RiskMonitor,
    RiskType,
    get_risk_monitor,
)

logger = logging.getLogger("ownex.auto_triggers")


class TriggerType(StrEnum):
    """Types of automatic triggers."""

    PHASE_PROGRESSION = "phase_progression"
    PHASE_DOWNGRADE = "phase_downgrade"
    RISK_WARNING = "risk_warning"
    EMERGENCY_STOP = "emergency_stop"
    POSITION_REDUCTION = "position_reduction"
    LEVERAGE_REDUCTION = "leverage_reduction"


class TriggerCondition:
    """Condition that triggers an action."""

    def check(self) -> bool:
        """Check if condition is met."""
        raise NotImplementedError


class PhaseProgressionTrigger(TriggerCondition):
    """Trigger for phase progression when all criteria met."""

    def __init__(self, scaling_manager: ProgressiveScalingManager):
        self.scaling_manager = scaling_manager

    def check(self) -> bool:
        """Check if phase progression criteria are met."""
        decision = self.scaling_manager.evaluate_progression()
        return decision.can_progress


class RiskLimitTrigger(TriggerCondition):
    """Trigger when risk limits are exceeded."""

    def __init__(self, risk_monitor: RiskMonitor, risk_type: RiskType, level: RiskLevel):
        self.risk_monitor = risk_monitor
        self.risk_type = risk_type
        self.level = level

    def check(self) -> bool:
        """Check if risk level exceeds threshold."""
        threshold = self.risk_monitor._thresholds.get(self.risk_type)
        if not threshold:
            return False

        current = threshold.current_value
        if self.level == RiskLevel.CRITICAL:
            return current >= threshold.critical_limit
        elif self.level == RiskLevel.DANGER:
            return current >= threshold.danger_limit
        elif self.level == RiskLevel.WARNING:
            return current >= threshold.warning_limit
        elif self.level == RiskLevel.CAUTION:
            return current >= threshold.caution_limit
        return False


class AutoTriggerSystem:
    """System for automatic trigger execution."""

    def __init__(self):
        self.scaling_manager = get_progressive_scaling_manager()
        self.risk_monitor = get_risk_monitor()
        self._triggers: list[tuple[TriggerCondition, TriggerType, callable]] = []
        self._setup_default_triggers()

    def _setup_default_triggers(self) -> None:
        """Setup default automatic triggers."""
        # Phase progression trigger
        self._triggers.append(
            (
                PhaseProgressionTrigger(self.scaling_manager),
                TriggerType.PHASE_PROGRESSION,
                self._execute_phase_progression,
            )
        )

        # Risk downgrade triggers
        self._triggers.append(
            (
                RiskLimitTrigger(self.risk_monitor, RiskType.DRAWDOWN, RiskLevel.DANGER),
                TriggerType.PHASE_DOWNGRADE,
                self._execute_phase_downgrade,
            )
        )

        # Emergency stop trigger
        self._triggers.append(
            (
                RiskLimitTrigger(self.risk_monitor, RiskType.DRAWDOWN, RiskLevel.CRITICAL),
                TriggerType.EMERGENCY_STOP,
                self._execute_emergency_stop,
            )
        )

    def _execute_phase_progression(self) -> None:
        """Execute phase progression."""
        logger.info("Phase progression trigger activated")
        success = self.scaling_manager.progress_to_next_phase()
        if success:
            new_config = self.scaling_manager.get_current_config()
            logger.info(f"Progressed to new phase: {new_config.name}")
            # Update risk thresholds for new phase
            self._update_risk_thresholds_for_phase(new_config)
        else:
            logger.warning("Phase progression failed - criteria not met")

    def _execute_phase_downgrade(self) -> None:
        """Execute phase downgrade due to excessive risk."""
        logger.warning("Phase downgrade trigger activated")
        prev_phase = self.scaling_manager.evaluate_downgrade()
        if prev_phase:
            self.scaling_manager.downgrade_to_phase(prev_phase)
            logger.info(f"Downgraded to {prev_phase}")
            # Update risk thresholds for downgraded phase
            new_config = self.scaling_manager.get_current_config()
            self._update_risk_thresholds_for_phase(new_config)

    def _execute_emergency_stop(self) -> None:
        """Execute emergency stop."""
        logger.critical("EMERGENCY STOP trigger activated")
        # Close all positions
        self.risk_monitor._close_all_positions()
        # Force downgrade to Phase 1
        self.scaling_manager.downgrade_to_phase(ScalingPhase.PHASE_1)
        logger.critical("Emergency stop executed - downgraded to Phase 1")

    def _update_risk_thresholds_for_phase(self, config) -> None:
        """Update risk thresholds based on phase configuration."""
        # Update drawdown limit
        drawdown_threshold = self.risk_monitor._thresholds[RiskType.DRAWDOWN]
        drawdown_threshold.danger_limit = config.drawdown_limit_pct
        drawdown_threshold.warning_limit = config.drawdown_limit_pct * 0.75
        drawdown_threshold.caution_limit = config.drawdown_limit_pct * 0.5

        # Update leverage limit
        leverage_threshold = self.risk_monitor._thresholds[RiskType.LEVERAGE]
        leverage_threshold.danger_limit = config.freqtrade_leverage
        leverage_threshold.warning_limit = config.freqtrade_leverage * 0.75
        leverage_threshold.caution_limit = config.freqtrade_leverage * 0.5

        logger.info(f"Updated risk thresholds for {config.name}")

    def check_triggers(self) -> list[tuple[TriggerType, bool]]:
        """Check all triggers and return status."""
        results = []
        for condition, trigger_type, action in self._triggers:
            try:
                triggered = condition.check()
                results.append((trigger_type, triggered))
                if triggered:
                    logger.info(f"Trigger activated: {trigger_type}")
                    action()
            except Exception as e:
                logger.error(f"Error checking trigger {trigger_type}: {e}")
                results.append((trigger_type, False))
        return results

    def get_status(self) -> dict[str, any]:
        """Get trigger system status."""
        trigger_statuses = []
        for condition, trigger_type, _ in self._triggers:
            try:
                triggered = condition.check()
                trigger_statuses.append({
                    "type": trigger_type.value,
                    "triggered": triggered,
                })
            except Exception as e:
                trigger_statuses.append({
                    "type": trigger_type.value,
                    "triggered": False,
                    "error": str(e),
                })

        return {
            "triggers": trigger_statuses,
            "scaling_phase": self.scaling_manager.get_current_phase().value,
            "risk_level": self.risk_monitor.get_current_level().value,
        }


# Singleton instance
_global_trigger_system: AutoTriggerSystem | None = None


def get_auto_trigger_system() -> AutoTriggerSystem:
    """Get or create the global auto trigger system."""
    global _global_trigger_system
    if _global_trigger_system is None:
        _global_trigger_system = AutoTriggerSystem()
    return _global_trigger_system
