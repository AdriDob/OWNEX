"""Execution Queue → Revenue Tracker Sync.

Connects the canonical execution queue (ExecState.PAID) to the revenue tracker
so that capital snapshots reflect real earnings from completed executions.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from core.execution_queue import ExecState
from cores.events.event_bus import get_event_bus
from cores.ledger import LedgerEvent, record_event
from cores.revenue_tracker import (
    PaymentPlatform,
    PaymentStatus,
    RevenueOpportunity,
    get_revenue_tracker,
)

logger = logging.getLogger("ownex.financial.execution_sync")

# Mapping from execution queue platform names to revenue tracker platforms
_PLATFORM_MAP = {
    "hackerone": "bug_bounty",
    "bugcrowd": "bug_bounty",
    "intigriti": "bug_bounty",
    "yeswehack": "bug_bounty",
    "immunefi": "bug_bounty",
    "synack": "bug_bounty",
    "algora": "dev_bounty",
    "opire": "dev_bounty",
    "freelancer": "dev_bounty",
    "issuehunt": "dev_bounty",
    "mindrift": "data_annotation",
    "outlier": "data_annotation",
}

_PAYMENT_PLATFORM_MAP = {
    "bug_bounty": PaymentPlatform.BUG_BOUNTY,
    "dev_bounty": PaymentPlatform.DEV_BOUNTY,
    "data_annotation": PaymentPlatform.DATA_ANNOTATION,
}


def _map_platform(exec_platform: str) -> str:
    """Map executor platform to revenue tracker platform category."""
    return _PLATFORM_MAP.get(exec_platform.lower(), "bug_bounty")


def _map_payment_platform(revenue_platform: str) -> PaymentPlatform:
    """Map revenue platform to PaymentPlatform enum."""
    return _PAYMENT_PLATFORM_MAP.get(revenue_platform, PaymentPlatform.BUG_BOUNTY)


class ExecutionRevenueSync:
    """Syncs execution queue PAID transitions to revenue tracker and ledger."""

    def __init__(self):
        self.tracker = get_revenue_tracker()
        self.event_bus = get_event_bus()
        self._initialized = False

    def initialize(self):
        """Initialize event subscriptions."""
        if self._initialized:
            return
        self.event_bus.subscribe("execution:state_changed", self._on_state_changed)
        self._initialized = True
        logger.info("ExecutionRevenueSync initialized")

    def _on_state_changed(self, **data):
        """Handle execution queue state change events."""
        item_id = data.get("item_id")
        new_state = data.get("new_state")
        payload = data.get("payload", {})

        if not item_id or new_state != ExecState.PAID.value:
            return

        logger.info(f"[SYNC] Execution {item_id} reached PAID, syncing to revenue tracker")

        try:
            self._sync_paid_execution(item_id, payload)
        except Exception as e:
            logger.error(f"Failed to sync paid execution {item_id}: {e}")

    def _sync_paid_execution(self, item_id: str, payload: dict[str, Any]):
        """Create/update revenue opportunity from a paid execution."""
        platform = payload.get("platform", "").lower()
        revenue_platform = _map_platform(platform)

        opp_id = f"exec_{item_id}"
        amount = Decimal(str(payload.get("reward", payload.get("amount", 0))))
        currency = payload.get("currency", "USD")

        # Check if opportunity already exists
        existing = self.tracker.opportunities.get(opp_id)

        if existing:
            # Update existing opportunity to PAID
            self.tracker.update_opportunity_status(
                opp_id,
                PaymentStatus.PAID,
                {
                    "execution_item_id": item_id,
                    "paid_at": datetime.now(UTC).isoformat(),
                    "platform": platform,
                },
            )
            logger.info(f"Updated existing opportunity {opp_id} to PAID")
        else:
            # Create new opportunity as PAID
            opportunity = RevenueOpportunity(
                id=opp_id,
                platform=revenue_platform,
                title=payload.get("title", f"Execution {item_id}"),
                description=payload.get("description", ""),
                amount=amount,
                currency=currency,
                status=PaymentStatus.PAID,
                provider_info={
                    "execution_item_id": item_id,
                    "executor_platform": platform,
                    "paid_at": datetime.now(UTC).isoformat(),
                },
                tracking_data={
                    "execution_id": item_id,
                    "source": "execution_queue",
                },
            )
            self.tracker.create_opportunity(opportunity)
            logger.info(f"Created new opportunity {opp_id} from execution (PAID)")

        # Record ledger entry for truth layer
        try:
            record_event(
                event=LedgerEvent.PAYOUT_RECEIVED,
                amount=float(amount),
                currency=currency,
                description=f"Execution {item_id}: {payload.get('title', 'Bounty completed')}",
                source="execution_queue",
                source_id=item_id,
                platform=revenue_platform,
                metadata={
                    "execution_item_id": item_id,
                    "executor_platform": platform,
                    "opportunity_id": opp_id,
                },
            )
            logger.info(f"Recorded ledger entry for execution {item_id}: {amount} {currency}")
        except Exception as e:
            logger.warning(f"Failed to record ledger entry for {item_id}: {e}")

        # Emit financial event
        self.event_bus.publish(
            "financial:execution_paid",
            **{
                "item_id": item_id,
                "opportunity_id": opp_id,
                "amount": float(amount),
                "currency": currency,
                "platform": revenue_platform,
                "paid_at": datetime.now(UTC).isoformat(),
            },
        )


# Singleton
_execution_revenue_sync: ExecutionRevenueSync | None = None


def get_execution_revenue_sync() -> ExecutionRevenueSync:
    """Get or create the execution-revenue sync instance."""
    global _execution_revenue_sync
    if _execution_revenue_sync is None:
        _execution_revenue_sync = ExecutionRevenueSync()
    return _execution_revenue_sync


def init_execution_revenue_sync() -> ExecutionRevenueSync:
    """Initialize and return the execution-revenue sync."""
    sync = get_execution_revenue_sync()
    sync.initialize()
    return sync
