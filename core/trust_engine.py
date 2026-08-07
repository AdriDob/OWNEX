"""Trust Engine — Platform-specific trust and auto-approval system.

Learns from historical outcomes to determine when auto-approval is safe.
Implements configurable trust thresholds per platform and work type.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.trust_engine")


class TrustLevel(StrEnum):
    """Trust level for a platform/work type combination."""

    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TrustMetrics:
    """Historical trust metrics for a platform."""

    platform: str
    total_opportunities: int = 0
    accepted: int = 0
    rejected: int = 0
    paid: int = 0
    unpaid: int = 0
    total_earnings_usd: float = 0.0
    avg_payment_usd: float = 0.0
    avg_time_to_payment_days: float = 0.0
    success_rate: float = 0.0
    payment_rate: float = 0.0
    last_updated: str = ""
    trust_level: TrustLevel = TrustLevel.UNKNOWN

    def calculate_scores(self) -> None:
        """Calculate derived scores from raw metrics."""
        if self.total_opportunities > 0:
            self.success_rate = self.accepted / self.total_opportunities
        if self.accepted > 0:
            self.payment_rate = self.paid / self.accepted
        if self.paid > 0:
            self.avg_payment_usd = self.total_earnings_usd / self.paid

        # Determine trust level
        if self.total_opportunities < 5:
            self.trust_level = TrustLevel.UNKNOWN
        elif self.success_rate >= 0.8 and self.payment_rate >= 0.9:
            self.trust_level = TrustLevel.HIGH
        elif self.success_rate >= 0.6 and self.payment_rate >= 0.7:
            self.trust_level = TrustLevel.MEDIUM
        elif self.success_rate >= 0.4:
            self.trust_level = TrustLevel.LOW
        else:
            self.trust_level = TrustLevel.CRITICAL

        self.last_updated = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "total_opportunities": self.total_opportunities,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "paid": self.paid,
            "unpaid": self.unpaid,
            "total_earnings_usd": self.total_earnings_usd,
            "avg_payment_usd": self.avg_payment_usd,
            "avg_time_to_payment_days": self.avg_time_to_payment_days,
            "success_rate": self.success_rate,
            "payment_rate": self.payment_rate,
            "trust_level": self.trust_level.value,
            "last_updated": self.last_updated,
        }


@dataclass
class AutoApprovalConfig:
    """Auto-approval configuration."""

    enabled: bool = False
    min_trust_level: TrustLevel = TrustLevel.HIGH
    max_amount_usd: float = 50.0
    require_confirmed_payment_history: bool = True
    min_confirmed_payments: int = 3
    allowed_platforms: list[str] = field(default_factory=list)
    blocked_platforms: list[str] = field(default_factory=list)


class TrustEngine:
    """Manages trust metrics and auto-approval decisions."""

    def __init__(self, storage_path: str | Path = "~/.ownex/trust.json"):
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._metrics: dict[str, TrustMetrics] = {}
        self._config: AutoApprovalConfig = AutoApprovalConfig()
        self._load()

    def _load(self) -> None:
        """Load metrics and config from storage."""
        if not self.storage_path.exists():
            return

        import json

        try:
            data = json.loads(self.storage_path.read_text())
            for platform, m_data in data.get("metrics", {}).items():
                metrics = TrustMetrics(platform=platform)
                for key, value in m_data.items():
                    if key == "trust_level":
                        metrics.trust_level = TrustLevel(value)
                    elif hasattr(metrics, key):
                        setattr(metrics, key, value)
                self._metrics[platform] = metrics

            config_data = data.get("config", {})
            self._config = AutoApprovalConfig(
                enabled=config_data.get("enabled", False),
                min_trust_level=TrustLevel(config_data.get("min_trust_level", "high")),
                max_amount_usd=config_data.get("max_amount_usd", 50.0),
                require_confirmed_payment_history=config_data.get("require_confirmed_payment_history", True),
                min_confirmed_payments=config_data.get("min_confirmed_payments", 3),
                allowed_platforms=config_data.get("allowed_platforms", []),
                blocked_platforms=config_data.get("blocked_platforms", []),
            )
            logger.info(f"[TRUST_ENGINE] Loaded {len(self._metrics)} platform metrics")
        except Exception as e:
            logger.error(f"[TRUST_ENGINE] Failed to load: {e}")

    def _save(self) -> None:
        """Save metrics and config to storage."""
        import json

        data = {
            "metrics": {platform: m.to_dict() for platform, m in self._metrics.items()},
            "config": {
                "enabled": self._config.enabled,
                "min_trust_level": self._config.min_trust_level.value,
                "max_amount_usd": self._config.max_amount_usd,
                "require_confirmed_payment_history": self._config.require_confirmed_payment_history,
                "min_confirmed_payments": self._config.min_confirmed_payments,
                "allowed_platforms": self._config.allowed_platforms,
                "blocked_platforms": self._config.blocked_platforms,
            },
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self.storage_path.write_text(json.dumps(data, indent=2))

    def record_outcome(
        self,
        platform: str,
        accepted: bool,
        paid: bool = False,
        amount_usd: float = 0.0,
        time_to_payment_days: float | None = None,
    ) -> None:
        """Record an outcome (accepted/rejected, paid/unpaid)."""
        if platform not in self._metrics:
            self._metrics[platform] = TrustMetrics(platform=platform)

        metrics = self._metrics[platform]
        metrics.total_opportunities += 1

        if accepted:
            metrics.accepted += 1
            if paid:
                metrics.paid += 1
                metrics.total_earnings_usd += amount_usd
                if time_to_payment_days is not None:
                    # Update moving average
                    n = metrics.paid
                    metrics.avg_time_to_payment_days = (
                        (metrics.avg_time_to_payment_days * (n - 1) + time_to_payment_days) / n
                    )
            else:
                metrics.unpaid += 1
        else:
            metrics.rejected += 1

        metrics.calculate_scores()
        self._save()
        logger.info(f"[TRUST_ENGINE] Recorded outcome for {platform}: accepted={accepted}, paid={paid}")

    def can_auto_approve(self, platform: str, amount_usd: float) -> tuple[bool, str]:
        """Determine if an opportunity can be auto-approved."""
        if not self._config.enabled:
            return False, "Auto-approval disabled globally"

        if platform in self._config.blocked_platforms:
            return False, f"Platform {platform} is blocked from auto-approval"

        if self._config.allowed_platforms and platform not in self._config.allowed_platforms:
            return False, f"Platform {platform} not in allowed list"

        if amount_usd > self._config.max_amount_usd:
            return False, f"Amount ${amount_usd} exceeds auto-approval threshold ${self._config.max_amount_usd}"

        metrics = self._metrics.get(platform)
        if not metrics:
            return False, f"No trust data for platform {platform}"

        if self._config.require_confirmed_payment_history and metrics.paid < self._config.min_confirmed_payments:
            return False, f"Insufficient confirmed payments ({metrics.paid} < {self._config.min_confirmed_payments})"

        # Check trust level
        trust_levels_order = [TrustLevel.UNKNOWN, TrustLevel.LOW, TrustLevel.MEDIUM, TrustLevel.HIGH, TrustLevel.CRITICAL]
        current_level_index = trust_levels_order.index(metrics.trust_level)
        required_level_index = trust_levels_order.index(self._config.min_trust_level)

        if current_level_index < required_level_index:
            return False, f"Trust level {metrics.trust_level.value} below minimum {self._config.min_trust_level.value}"

        return True, "All auto-approval criteria met"

    def get_platform_trust(self, platform: str) -> TrustMetrics | None:
        """Get trust metrics for a platform."""
        return self._metrics.get(platform)

    def get_all_trust_metrics(self) -> dict[str, TrustMetrics]:
        """Get trust metrics for all platforms."""
        return self._metrics

    def update_config(self, **kwargs: Any) -> None:
        """Update auto-approval configuration."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                if key == "min_trust_level" and isinstance(value, str):
                    setattr(self._config, key, TrustLevel(value))
                else:
                    setattr(self._config, key, value)
        self._save()
        logger.info(f"[TRUST_ENGINE] Updated config: {kwargs}")

    def get_config(self) -> AutoApprovalConfig:
        """Get current auto-approval configuration."""
        return self._config

    def get_status(self) -> dict[str, Any]:
        """Get overall status of the trust engine."""
        platforms_with_high_trust = [p for p, m in self._metrics.items() if m.trust_level == TrustLevel.HIGH]
        platforms_with_data = len(self._metrics)

        return {
            "platforms_with_data": platforms_with_data,
            "platforms_with_high_trust": len(platforms_with_high_trust),
            "high_trust_platforms": platforms_with_high_trust,
            "auto_approval_enabled": self._config.enabled,
            "auto_approval_threshold_usd": self._config.max_amount_usd,
            "min_trust_level": self._config.min_trust_level.value,
            "total_opportunities_tracked": sum(m.total_opportunities for m in self._metrics.values()),
            "total_earnings_tracked_usd": sum(m.total_earnings_usd for m in self._metrics.values()),
        }


_engine: TrustEngine | None = None


def get_trust_engine() -> TrustEngine:
    """Get the singleton TrustEngine instance."""
    global _engine
    if _engine is None:
        _engine = TrustEngine()
    return _engine
