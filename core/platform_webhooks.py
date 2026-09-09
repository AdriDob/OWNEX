"""Platform Webhook Integrators — Real webhook handlers for platforms.

Integrates with HackerOne, Opire, Freelancer webhooks to detect payments automatically.
"""

from __future__ import annotations

import logging
from typing import Any

from .payment_tracker import get_payment_tracker

logger = logging.getLogger("ownex.platform_webhooks")


class HackerOneWebhookHandler:
    """HackerOne webhook handler for payment detection."""

    @staticmethod
    def handle_webhook(payload: dict[str, Any]) -> dict[str, Any]:
        """Process HackerOne webhook payload."""
        # HackerOne sends bounties as rewards
        if payload.get("type") == "reward":
            amount = float(payload.get("amount", 0))
            if amount > 0:
                tracker = get_payment_tracker()
                payment = tracker.receive_webhook(
                    platform="hackerone",
                    payload={
                        "id": payload.get("id"),
                        "opportunity_id": payload.get("report_id"),
                        "amount": amount,
                        "currency": "USD",
                        "type": "reward",
                    },
                )
                logger.info(f"[HACKERONE] Payment detected: ${amount}")
                return {"success": True, "payment_id": payment.id}
        return {"success": False, "reason": "Not a payment event"}


class OpireWebhookHandler:
    """Opire webhook handler for payment detection."""

    @staticmethod
    def handle_webhook(payload: dict[str, Any]) -> dict[str, Any]:
        """Process Opire webhook payload."""
        # Opire sends payment confirmations
        if payload.get("event") == "payment_received":
            amount = float(payload.get("amount", 0))
            if amount > 0:
                tracker = get_payment_tracker()
                payment = tracker.receive_webhook(
                    platform="opire",
                    payload={
                        "id": payload.get("payment_id"),
                        "opportunity_id": payload.get("bounty_id"),
                        "amount": amount,
                        "currency": "USD",
                        "event": "payment_received",
                    },
                )
                logger.info(f"[OPIRE] Payment detected: ${amount}")
                return {"success": True, "payment_id": payment.id}
        return {"success": False, "reason": "Not a payment event"}


class FreelancerWebhookHandler:
    """Freelancer webhook handler for payment detection."""

    @staticmethod
    def handle_webhook(payload: dict[str, Any]) -> dict[str, Any]:
        """Process Freelancer webhook payload."""
        # Freelancer sends payment confirmations
        if payload.get("type") == "payment":
            amount = float(payload.get("amount", 0))
            if amount > 0:
                tracker = get_payment_tracker()
                payment = tracker.receive_webhook(
                    platform="freelancer",
                    payload={
                        "id": payload.get("payment_id"),
                        "opportunity_id": payload.get("project_id"),
                        "amount": amount,
                        "currency": "USD",
                        "type": "payment",
                    },
                )
                logger.info(f"[FREELANCER] Payment detected: ${amount}")
                return {"success": True, "payment_id": payment.id}
        return {"success": False, "reason": "Not a payment event"}


# Registry of webhook handlers
WEBHOOK_HANDLERS = {
    "hackerone": HackerOneWebhookHandler,
    "opire": OpireWebhookHandler,
    "freelancer": FreelancerWebhookHandler,
}


def handle_platform_webhook(platform: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Route webhook to appropriate platform handler."""
    handler = WEBHOOK_HANDLERS.get(platform.lower())
    if handler:
        return handler.handle_webhook(payload)
    return {"success": False, "reason": f"No handler for platform: {platform}"}
