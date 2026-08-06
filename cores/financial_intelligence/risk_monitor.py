"""Risk Monitor System — Real-time risk tracking and automatic safety triggers.

Monitors all risk parameters and triggers automatic responses when limits are exceeded:
- Drawdown limits
- Leverage limits
- Position sizing limits
- Stop-loss violations
- Platform-specific risks
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

logger = logging.getLogger("ownex.risk_monitor")


class RiskLevel(StrEnum):
    """Current risk level."""

    SAFE = "safe"
    CAUTION = "caution"
    WARNING = "warning"
    DANGER = "danger"
    CRITICAL = "critical"


class RiskType(StrEnum):
    """Types of risks to monitor."""

    DRAWDOWN = "drawdown"
    LEVERAGE = "leverage"
    POSITION_SIZE = "position_size"
    STOP_LOSS = "stop_loss"
    PLATFORM_RISK = "platform_risk"
    LIQUIDITY = "liquidity"
    CONCENTRATION = "concentration"


@dataclass
class RiskThreshold:
    """Risk threshold configuration."""

    risk_type: RiskType
    safe_limit: float
    caution_limit: float
    warning_limit: float
    danger_limit: float
    critical_limit: float
    current_value: float = 0.0
    triggered: bool = False
    last_triggered: datetime | None = None


@dataclass
class RiskAlert:
    """Risk alert information."""

    risk_type: RiskType
    level: RiskLevel
    current_value: float
    limit: float
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    action_required: bool = False
    action_taken: str | None = None


@dataclass
class RiskAction:
    """Automatic action to take when risk threshold is triggered."""

    risk_type: RiskType
    trigger_level: RiskLevel
    action: Callable[[], None]
    description: str


class RiskMonitor:
    """Real-time risk monitoring system."""

    def __init__(self):
        self._thresholds: dict[RiskType, RiskThreshold] = {}
        self._alerts: list[RiskAlert] = []
        self._actions: list[RiskAction] = []
        self._current_level = RiskLevel.SAFE
        self._setup_default_thresholds()
        self._setup_default_actions()

    def _setup_default_thresholds(self) -> None:
        """Setup default risk thresholds."""
        self._thresholds = {
            RiskType.DRAWDOWN: RiskThreshold(
                risk_type=RiskType.DRAWDOWN,
                safe_limit=0.05,  # 5%
                caution_limit=0.10,  # 10%
                warning_limit=0.15,  # 15%
                danger_limit=0.25,  # 25%
                critical_limit=0.40,  # 40%
            ),
            RiskType.LEVERAGE: RiskThreshold(
                risk_type=RiskType.LEVERAGE,
                safe_limit=5.0,
                caution_limit=10.0,
                warning_limit=15.0,
                danger_limit=25.0,
                critical_limit=50.0,
            ),
            RiskType.POSITION_SIZE: RiskThreshold(
                risk_type=RiskType.POSITION_SIZE,
                safe_limit=0.10,  # 10% of capital
                caution_limit=0.20,  # 20%
                warning_limit=0.30,  # 30%
                danger_limit=0.50,  # 50%
                critical_limit=0.80,  # 80%
            ),
            RiskType.STOP_LOSS: RiskThreshold(
                risk_type=RiskType.STOP_LOSS,
                safe_limit=0.02,  # 2%
                caution_limit=0.03,  # 3%
                warning_limit=0.05,  # 5%
                danger_limit=0.08,  # 8%
                critical_limit=0.15,  # 15%
            ),
            RiskType.PLATFORM_RISK: RiskThreshold(
                risk_type=RiskType.PLATFORM_RISK,
                safe_limit=0.20,  # 20% of capital on one platform
                caution_limit=0.40,
                warning_limit=0.60,
                danger_limit=0.80,
                critical_limit=1.0,
            ),
            RiskType.CONCENTRATION: RiskThreshold(
                risk_type=RiskType.CONCENTRATION,
                safe_limit=0.30,  # 30% in one asset
                caution_limit=0.50,
                warning_limit=0.70,
                danger_limit=0.85,
                critical_limit=1.0,
            ),
        }

    def _setup_default_actions(self) -> None:
        """Setup default automatic actions."""
        self._actions = [
            RiskAction(
                risk_type=RiskType.DRAWDOWN,
                trigger_level=RiskLevel.WARNING,
                action=lambda: self._reduce_positions(0.5),
                description="Reduce positions by 50%",
            ),
            RiskAction(
                risk_type=RiskType.DRAWDOWN,
                trigger_level=RiskLevel.DANGER,
                action=lambda: self._reduce_positions(0.8),
                description="Reduce positions by 80%",
            ),
            RiskAction(
                risk_type=RiskType.DRAWDOWN,
                trigger_level=RiskLevel.CRITICAL,
                action=lambda: self._close_all_positions(),
                description="Close all positions (emergency)",
            ),
            RiskAction(
                risk_type=RiskType.LEVERAGE,
                trigger_level=RiskLevel.WARNING,
                action=lambda: self._reduce_leverage(0.7),
                description="Reduce leverage by 30%",
            ),
            RiskAction(
                risk_type=RiskType.LEVERAGE,
                trigger_level=RiskLevel.DANGER,
                action=lambda: self._reduce_leverage(0.5),
                description="Reduce leverage by 50%",
            ),
        ]

    def update_risk_value(self, risk_type: RiskType, value: float) -> None:
        """Update current risk value and check thresholds."""
        if risk_type not in self._thresholds:
            logger.warning(f"Unknown risk type: {risk_type}")
            return

        threshold = self._thresholds[risk_type]
        threshold.current_value = value

        # Check if threshold triggered
        self._check_threshold(threshold)

    def _check_threshold(self, threshold: RiskThreshold) -> None:
        """Check if threshold is triggered and take action."""
        current = threshold.current_value

        # Determine risk level
        if current >= threshold.critical_limit:
            level = RiskLevel.CRITICAL
        elif current >= threshold.danger_limit:
            level = RiskLevel.DANGER
        elif current >= threshold.warning_limit:
            level = RiskLevel.WARNING
        elif current >= threshold.caution_limit:
            level = RiskLevel.CAUTION
        else:
            level = RiskLevel.SAFE

        # Update global risk level
        self._current_level = max(self._current_level, level, key=lambda x: ["safe", "caution", "warning", "danger", "critical"].index(x))

        # Create alert if not safe
        if level != RiskLevel.SAFE:
            alert = RiskAlert(
                risk_type=threshold.risk_type,
                level=level,
                current_value=current,
                limit=threshold.critical_limit if level == RiskLevel.CRITICAL else (
                    threshold.danger_limit if level == RiskLevel.DANGER else (
                        threshold.warning_limit if level == RiskLevel.WARNING else threshold.caution_limit
                    )
                ),
                message=f"{threshold.risk_type.value} at {current:.1%} - {level.upper()}",
                action_required=level in [RiskLevel.DANGER, RiskLevel.CRITICAL],
            )
            self._alerts.append(alert)
            logger.warning(f"Risk alert: {alert.message}")

            # Trigger automatic action if required
            if alert.action_required:
                self._trigger_action(threshold.risk_type, level)

    def _trigger_action(self, risk_type: RiskType, level: RiskLevel) -> None:
        """Trigger automatic action for risk type and level."""
        for action in self._actions:
            if action.risk_type == risk_type and action.trigger_level == level:
                try:
                    action.action()
                    logger.info(f"Executed risk action: {action.description}")
                    # Update latest alert
                    if self._alerts:
                        self._alerts[-1].action_taken = action.description
                except Exception as e:
                    logger.error(f"Failed to execute risk action: {e}")

    def _reduce_positions(self, reduction_pct: float) -> None:
        """Reduce all positions by percentage."""
        # This would integrate with trading systems
        logger.info(f"Reducing positions by {reduction_pct:.0%}")
        # Implementation: call Freqtrade/Hummingbot APIs to reduce positions

    def _reduce_leverage(self, reduction_pct: float) -> None:
        """Reduce leverage by percentage."""
        logger.info(f"Reducing leverage by {reduction_pct:.0%}")
        # Implementation: update leverage settings in trading systems

    def _close_all_positions(self) -> None:
        """Close all positions (emergency)."""
        logger.critical("EMERGENCY: Closing all positions")
        # Implementation: call trading systems to close all positions

    def get_current_level(self) -> RiskLevel:
        """Get current overall risk level."""
        return self._current_level

    def get_alerts(self, since: datetime | None = None) -> list[RiskAlert]:
        """Get risk alerts since specified time."""
        if since is None:
            return self._alerts.copy()
        return [alert for alert in self._alerts if alert.timestamp >= since]

    def get_status(self) -> dict[str, any]:
        """Get current risk status."""
        return {
            "current_level": self._current_level.value,
            "thresholds": {
                risk_type.value: {
                    "current": threshold.current_value,
                    "safe": threshold.safe_limit,
                    "caution": threshold.caution_limit,
                    "warning": threshold.warning_limit,
                    "danger": threshold.danger_limit,
                    "critical": threshold.critical_limit,
                    "triggered": threshold.triggered,
                }
                for risk_type, threshold in self._thresholds.items()
            },
            "recent_alerts": [
                {
                    "type": alert.risk_type.value,
                    "level": alert.level.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "action_required": alert.action_required,
                    "action_taken": alert.action_taken,
                }
                for alert in self._alerts[-10:]  # Last 10 alerts
            ],
        }


# Singleton instance
_global_monitor: RiskMonitor | None = None


def get_risk_monitor() -> RiskMonitor:
    """Get or create the global risk monitor."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = RiskMonitor()
    return _global_monitor
