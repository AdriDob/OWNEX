"""Event publisher for AI Bounty Auto-Hunter events."""

from __future__ import annotations

import logging
from typing import Any

from cores.events.types import Events

logger = logging.getLogger("orion.ai_bounty.publisher")


class AIBountyEventPublisher:
    """Publishes AI bounty lifecycle events to EventBus.

    Designed to be a silent-safe no-op when EventBus is unavailable.
    """

    def __init__(self) -> None:
        self._bus = None

    def _get_bus(self):
        if self._bus is None:
            try:
                from cores.events.event_bus import get_event_bus

                self._bus = get_event_bus()
            except Exception:
                return None
        return self._bus

    def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        bus = self._get_bus()
        if bus is None:
            logger.debug("EventBus unavailable — dropping event %s", event_type)
            return
        try:
            bus.publish(event_type, payload)
        except Exception as exc:
            logger.warning("Failed to publish %s: %s", event_type, exc)

    def challenge_detected(
        self,
        platform: str,
        challenge_id: str,
        title: str,
        url: str,
        severity: str = "medium",
    ) -> None:
        self._publish(
            Events.AI_BOUNTY_CHALLENGE_DETECTED,
            {
                "platform": platform,
                "challenge_id": challenge_id,
                "title": title,
                "url": url,
                "severity": severity,
            },
        )

    def challenge_scanned(
        self,
        platform: str,
        challenge_id: str,
        findings_count: int,
        scan_duration_ms: float,
    ) -> None:
        self._publish(
            Events.AI_BOUNTY_CHALLENGE_SCANNED,
            {
                "platform": platform,
                "challenge_id": challenge_id,
                "findings_count": findings_count,
                "scan_duration_ms": scan_duration_ms,
            },
        )

    def report_ready(
        self,
        platform: str,
        challenge_id: str,
        report_id: int,
        findings_count: int,
        estimated_payout: float,
    ) -> None:
        self._publish(
            Events.AI_BOUNTY_REPORT_READY,
            {
                "platform": platform,
                "challenge_id": challenge_id,
                "report_id": report_id,
                "findings_count": findings_count,
                "estimated_payout": estimated_payout,
            },
        )

    def opportunity_assessed(
        self,
        platform: str,
        challenge_id: str,
        ev: float,
        effort_hours: float,
        action: str,
    ) -> None:
        self._publish(
            Events.AI_BOUNTY_OPPORTUNITY_ASSESSED,
            {
                "platform": platform,
                "challenge_id": challenge_id,
                "expected_value_per_hour": ev,
                "effort_hours": effort_hours,
                "recommended_action": action,
            },
        )
