"""Payment Tracker — Auto-detection of payments across platforms.

Monitors platforms for incoming payments and triggers closed-loop feedback.
Supports webhook receivers and polling for platforms without webhooks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.payment_tracker")


class PaymentStatus(StrEnum):
    """Status of a payment in the tracking system."""

    PENDING = "pending"
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    DISPUTED = "disputed"


@dataclass
class PaymentEvent:
    """A payment event detected from a platform."""

    id: str
    platform: str
    opportunity_id: str
    amount_usd: float
    currency: str
    status: PaymentStatus
    detected_at: str
    confirmed_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    webhook_payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "opportunity_id": self.opportunity_id,
            "amount_usd": self.amount_usd,
            "currency": self.currency,
            "status": self.status.value,
            "detected_at": self.detected_at,
            "confirmed_at": self.confirmed_at,
            "metadata": self.metadata,
        }


@dataclass
class PlatformWebhookConfig:
    """Webhook configuration for a platform."""

    platform: str
    webhook_url: str | None = None
    secret: str | None = None
    polling_enabled: bool = False
    polling_interval_hours: int = 24
    last_polled_at: str | None = None


class PaymentTracker:
    """Tracks payments across all platforms and triggers feedback loops."""

    def __init__(self, storage_path: str | Path = "~/.ownex/payments.json"):
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._payments: dict[str, PaymentEvent] = {}
        self._webhook_configs: dict[str, PlatformWebhookConfig] = {}
        self._load()

    def _load(self) -> None:
        """Load payments and configs from storage."""
        if not self.storage_path.exists():
            return

        import json

        try:
            data = json.loads(self.storage_path.read_text())
            for pid, p_data in data.get("payments", {}).items():
                self._payments[pid] = PaymentEvent(
                    id=pid,
                    platform=p_data["platform"],
                    opportunity_id=p_data["opportunity_id"],
                    amount_usd=p_data["amount_usd"],
                    currency=p_data["currency"],
                    status=PaymentStatus(p_data["status"]),
                    detected_at=p_data["detected_at"],
                    confirmed_at=p_data.get("confirmed_at"),
                    metadata=p_data.get("metadata", {}),
                )
            for platform, wc_data in data.get("webhook_configs", {}).items():
                self._webhook_configs[platform] = PlatformWebhookConfig(
                    platform=platform,
                    webhook_url=wc_data.get("webhook_url"),
                    secret=wc_data.get("secret"),
                    polling_enabled=wc_data.get("polling_enabled", False),
                    polling_interval_hours=wc_data.get("polling_interval_hours", 24),
                    last_polled_at=wc_data.get("last_polled_at"),
                )
            logger.info(
                f"[PAYMENT_TRACKER] Loaded {len(self._payments)} payments, {len(self._webhook_configs)} webhook configs"
            )
        except Exception as e:
            logger.error(f"[PAYMENT_TRACKER] Failed to load: {e}")

    def _save(self) -> None:
        """Save payments and configs to storage."""
        import json

        data = {
            "payments": {pid: p.to_dict() for pid, p in self._payments.items()},
            "webhook_configs": {
                platform: {
                    "platform": wc.platform,
                    "webhook_url": wc.webhook_url,
                    "secret": wc.secret,
                    "polling_enabled": wc.polling_enabled,
                    "polling_interval_hours": wc.polling_interval_hours,
                    "last_polled_at": wc.last_polled_at,
                }
                for platform, wc in self._webhook_configs.items()
            },
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self.storage_path.write_text(json.dumps(data, indent=2))

    def register_webhook_config(
        self,
        platform: str,
        webhook_url: str | None = None,
        secret: str | None = None,
        polling_enabled: bool = False,
        polling_interval_hours: int = 24,
    ) -> None:
        """Register webhook/polling config for a platform."""
        self._webhook_configs[platform] = PlatformWebhookConfig(
            platform=platform,
            webhook_url=webhook_url,
            secret=secret,
            polling_enabled=polling_enabled,
            polling_interval_hours=polling_interval_hours,
        )
        self._save()
        logger.info(f"[PAYMENT_TRACKER] Registered webhook config for {platform}")

    def receive_webhook(self, platform: str, payload: dict[str, Any]) -> PaymentEvent:
        """Process incoming webhook from a platform."""
        # Extract payment info from platform-specific payload
        payment_id = payload.get("id") or payload.get("payment_id") or f"webhook_{datetime.now(UTC).timestamp()}"
        opportunity_id = payload.get("opportunity_id") or payload.get("order_id") or "unknown"
        amount_usd = float(payload.get("amount", 0))
        currency = payload.get("currency", "USD")

        payment = PaymentEvent(
            id=payment_id,
            platform=platform,
            opportunity_id=opportunity_id,
            amount_usd=amount_usd,
            currency=currency,
            status=PaymentStatus.DETECTED,
            detected_at=datetime.now(UTC).isoformat(),
            metadata={"source": "webhook"},
            webhook_payload=payload,
        )

        self._payments[payment_id] = payment
        self._save()
        logger.info(f"[PAYMENT_TRACKER] Webhook received: {platform} - ${amount_usd} {currency}")
        return payment

    def poll_platform(self, platform: str) -> list[PaymentEvent]:
        """Poll a platform for new payments (fallback for platforms without webhooks)."""
        config = self._webhook_configs.get(platform)
        if not config or not config.polling_enabled:
            logger.warning(f"[PAYMENT_TRACKER] Polling not enabled for {platform}")
            return []

        # Check if it's time to poll
        if config.last_polled_at:
            last_polled = datetime.fromisoformat(config.last_polled_at)
            if datetime.now(UTC) - last_polled < timedelta(hours=config.polling_interval_hours):
                logger.debug(f"[PAYMENT_TRACKER] Skipping poll for {platform} (too soon)")
                return []

        # TODO: Implement platform-specific polling logic
        # For now, return empty
        logger.info(f"[PAYMENT_TRACKER] Polling {platform} (not implemented yet)")
        config.last_polled_at = datetime.now(UTC).isoformat()
        self._save()
        return []

    def confirm_payment(self, payment_id: str) -> PaymentEvent | None:
        """Mark a payment as confirmed (user verified or auto-confirmed)."""
        payment = self._payments.get(payment_id)
        if not payment:
            logger.warning(f"[PAYMENT_TRACKER] Payment not found: {payment_id}")
            return None

        payment.status = PaymentStatus.CONFIRMED
        payment.confirmed_at = datetime.now(UTC).isoformat()
        self._save()
        logger.info(f"[PAYMENT_TRACKER] Payment confirmed: {payment_id}")
        return payment

    def get_pending_payments(self) -> list[PaymentEvent]:
        """Get all payments pending confirmation."""
        return [p for p in self._payments.values() if p.status == PaymentStatus.DETECTED]

    def get_payments_by_platform(self, platform: str) -> list[PaymentEvent]:
        """Get all payments for a specific platform."""
        return [p for p in self._payments.values() if p.platform == platform]

    def get_total_earnings(self, days: int = 30) -> float:
        """Get total earnings in the last N days."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        total = 0.0
        for payment in self._payments.values():
            if payment.status == PaymentStatus.CONFIRMED:
                detected_at = datetime.fromisoformat(payment.detected_at)
                if detected_at >= cutoff:
                    total += payment.amount_usd
        return total

    def get_status(self) -> dict[str, Any]:
        """Get overall status of payment tracking."""
        pending = len(self.get_pending_payments())
        confirmed = len([p for p in self._payments.values() if p.status == PaymentStatus.CONFIRMED])
        total_earnings_30d = self.get_total_earnings(30)

        return {
            "total_payments": len(self._payments),
            "pending_confirmation": pending,
            "confirmed": confirmed,
            "total_earnings_30d_usd": total_earnings_30d,
            "platforms_with_webhooks": len([c for c in self._webhook_configs.values() if c.webhook_url]),
            "platforms_with_polling": len([c for c in self._webhook_configs.values() if c.polling_enabled]),
            "platforms": list(self._webhook_configs.keys()),
        }


_tracker: PaymentTracker | None = None


def get_payment_tracker() -> PaymentTracker:
    """Get the singleton PaymentTracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = PaymentTracker()
    return _tracker
