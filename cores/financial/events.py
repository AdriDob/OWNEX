"""Financial event definitions — connects money events to the notification system.

Every financial action publishes an event that flows through:
  EventBus → NotificationHub → Channels (email, WhatsApp, desktop, web)

Event types:
  financial:payout_received    — confirmed payout from platform
  financial:report_accepted    — report was accepted/paid
  financial:withdrawal_completed — withdrawal finalized
  financial:target_detected     — high-value target found
  financial:sync_completed      — platform sync finished
  financial:sync_failed         — platform sync failed
  financial:reconciliation_conflict — ledger mismatch detected
  financial:dispute_resolved    — discrepancy cleared
"""

from __future__ import annotations

import logging
from typing import Any

from cores.events.event_bus import EVENT_PRIORITY_MAP, get_event_bus
from cores.notifications.hub import get_hub
from cores.notifications.push import EVENT_PUSH_MAP

logger = logging.getLogger("ownex.financial.events")

FINANCIAL_EVENT_TYPES = [
    "financial:payout_received",
    "financial:report_accepted",
    "financial:withdrawal_completed",
    "financial:target_detected",
    "financial:sync_completed",
    "financial:sync_failed",
    "financial:reconciliation_conflict",
    "financial:dispute_resolved",
    "financial:withdrawal_failed",
    "financial:high_value_opportunity",
    "financial:crypto_sync_completed",
    "financial:crypto_sync_failed",
    "financial:crypto_deposit_detected",
    "financial:crypto_withdrawal_detected",
    "financial:crypto_staking_reward",
    "financial:crypto_defi_yield",
    "financial:crypto_airdrop",
]

FINANCIAL_EVENT_PRIORITIES: dict[str, str] = {
    "financial:payout_received": "high",
    "financial:report_accepted": "high",
    "financial:withdrawal_completed": "high",
    "financial:withdrawal_failed": "critical",
    "financial:target_detected": "high",
    "financial:high_value_opportunity": "high",
    "financial:reconciliation_conflict": "critical",
    "financial:sync_failed": "medium",
    "financial:sync_completed": "low",
    "financial:dispute_resolved": "medium",
    "financial:crypto_sync_completed": "low",
    "financial:crypto_sync_failed": "medium",
    "financial:crypto_deposit_detected": "high",
    "financial:crypto_withdrawal_detected": "high",
    "financial:crypto_staking_reward": "medium",
    "financial:crypto_defi_yield": "medium",
    "financial:crypto_airdrop": "high",
}

FINANCIAL_PUSH_MAP: dict[str, dict[str, Any]] = {
    "financial:payout_received": {
        "title": "💰 Pago recibido",
        "priority": "high",
        "icon": "money",
        "ttl": 86400,
    },
    "financial:report_accepted": {
        "title": "✅ Reporte aceptado",
        "priority": "high",
        "icon": "report",
        "ttl": 86400,
    },
    "financial:withdrawal_completed": {
        "title": "🏦 Retiro completado",
        "priority": "high",
        "icon": "withdrawal",
        "ttl": 86400,
    },
    "financial:withdrawal_failed": {
        "title": "⚠️ Retiro fallido",
        "priority": "critical",
        "icon": "error",
        "ttl": 7200,
    },
    "financial:target_detected": {
        "title": "🎯 Oportunidad detectada",
        "priority": "high",
        "icon": "target",
        "ttl": 86400,
    },
    "financial:reconciliation_conflict": {
        "title": "🔍 Discrepancia detectada",
        "priority": "critical",
        "icon": "warning",
        "ttl": 43200,
    },
    "financial:sync_failed": {
        "title": "🔄 Sincronización fallida",
        "priority": "medium",
        "icon": "sync",
        "ttl": 3600,
    },
    "financial:sync_completed": {
        "title": "✅ Sincronización completada",
        "priority": "low",
        "icon": "sync",
        "ttl": 1800,
    },
    "financial:crypto_sync_completed": {
        "title": "⛓️ Wallet sync OK",
        "priority": "low",
        "icon": "wallet",
        "ttl": 1800,
    },
    "financial:crypto_sync_failed": {
        "title": "⛓️ Wallet sync failed",
        "priority": "medium",
        "icon": "wallet",
        "ttl": 3600,
    },
    "financial:crypto_deposit_detected": {
        "title": "💰 Crypto deposit",
        "priority": "high",
        "icon": "money",
        "ttl": 86400,
    },
    "financial:crypto_withdrawal_detected": {
        "title": "💸 Crypto withdrawal",
        "priority": "high",
        "icon": "withdrawal",
        "ttl": 86400,
    },
    "financial:crypto_airdrop": {
        "title": "🪂 Airdrop detected",
        "priority": "high",
        "icon": "money",
        "ttl": 86400,
    },
}

# Register financial events
EVENT_PRIORITY_MAP.update(FINANCIAL_EVENT_PRIORITIES)
EVENT_PUSH_MAP.update(FINANCIAL_PUSH_MAP)


def publish_financial_event(
    event_type: str,
    amount: float = 0.0,
    currency: str = "USD",
    platform: str = "",
    description: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    bus = get_event_bus()
    bus.publish(
        event_type,
        amount=amount,
        currency=currency,
        platform=platform,
        message=description,
        id=f"{event_type}-{abs(hash(description)) % 100000}",
        metadata=metadata or {},
    )
    logger.info("Financial event: %s — %.2f %s (%s)", event_type, amount, currency, description[:60])


def register_financial_event_bridge() -> None:
    """Subscribe to financial events and route them through the notification hub."""
    hub = get_hub()
    bus = get_event_bus()

    def _on_financial_event(event_type: str, **payload: Any) -> None:
        if not event_type.startswith("financial:"):
            return

        push_info = FINANCIAL_PUSH_MAP.get(event_type, {})
        title = push_info.get("title", event_type.replace("financial:", "").replace("_", " ").title())
        amount = payload.get("amount", 0)
        currency = payload.get("currency", "USD")
        platform = payload.get("platform", "")

        message = payload.get("message", "") or payload.get("description", "")
        if amount and not message:
            message = f"{title}: {amount:.2f} {currency}"
            if platform:
                message += f" ({platform})"

        priority = FINANCIAL_EVENT_PRIORITIES.get(event_type, "medium")

        channels = ["web"]
        if priority in ("high", "critical"):
            channels.append("desktop")
        if event_type in (
            "financial:withdrawal_failed",
            "financial:reconciliation_conflict",
            "financial:payout_received",
        ):
            channels.append("mobile")

        hub.notify(
            type_=event_type.replace(":", "_"),
            title=title,
            message=str(message)[:500],
            severity=priority,
            priority=priority,
            channels=channels,
            metadata={"event_type": event_type, "amount": amount, "currency": currency, **payload},
            dedup_key=f"{event_type}-{payload.get('id', '')}",
        )

    for etype in FINANCIAL_EVENT_TYPES:
        bus.subscribe(etype, _on_financial_event)
    logger.info("Financial event bridge registered — %d events routed", len(FINANCIAL_EVENT_TYPES))


def init_financial_events() -> None:
    """Call at startup to register priorities, push maps, and the event bridge."""
    register_financial_event_bridge()
    logger.info("Financial events initialized")
