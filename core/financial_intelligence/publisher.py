from __future__ import annotations

import logging
from typing import Any

from core.financial_intelligence.models import F1Message, Opportunity

logger = logging.getLogger("orion.financial_intelligence.publisher")


class FinancialIntelligencePublisher:
    """Publishes Financial Intelligence events to the EventBus.

    Never calls EventBus directly — uses an optional bind callback
    to allow loose coupling.
    """

    def __init__(self):
        self._publish: Any = None

    def bind(self, publish_fn: Any) -> None:
        self._publish = publish_fn

    def opportunity_evaluated(self, opp: Opportunity, council_result: dict[str, Any]) -> None:
        self._try_publish(
            "financial_intelligence:opportunity:evaluated",
            {
                "label": opp.label,
                "source": opp.source,
                "expected_value": opp.expected_value,
                "priority_score": opp.priority_score,
                "consensus_score": opp.consensus_score,
                "blocked": council_result.get("blocked", False),
                "risk_score": opp.risk_score,
                "model_confidence": opp.model_confidence,
            },
        )

    def opportunity_accepted(self, opp: Opportunity) -> None:
        self._try_publish(
            "financial_intelligence:opportunity:accepted",
            {
                "label": opp.label,
                "source": opp.source,
                "expected_value": opp.expected_value,
            },
        )

    def opportunity_rejected(self, opp: Opportunity, reasons: list[str]) -> None:
        self._try_publish(
            "financial_intelligence:opportunity:rejected",
            {
                "label": opp.label,
                "source": opp.source,
                "reasons": reasons,
            },
        )

    def risk_alert_triggered(self, alert_type: str, details: dict[str, Any]) -> None:
        self._try_publish(
            "financial_intelligence:risk:alert",
            {
                "alert_type": alert_type,
                "details": details,
            },
        )

    def f1_message_sent(self, msg: F1Message) -> None:
        self._try_publish("financial_intelligence:f1:message", msg.to_dict())

    def daily_briefing_ready(self, opportunities_count: int, portfolio_value: float) -> None:
        self._try_publish(
            "financial_intelligence:briefing:ready",
            {
                "opportunities_count": opportunities_count,
                "portfolio_value": portfolio_value,
            },
        )

    def _try_publish(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._publish is None:
            logger.debug("[PUB] No publisher bound — event %s not sent", event_type)
            return
        try:
            self._publish(event_type, **payload)
            logger.info("[PUB] %s published", event_type)
        except Exception as exc:
            logger.warning("[PUB] Failed to publish %s: %s", event_type, exc)
