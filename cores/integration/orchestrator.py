"""Integration Orchestrator — Rastro as an Intelligent Hub.

Coordinates FASE 1 (Mission Control), FASE 2 (Security Cycle), FASE 3 (Opportunity Engine) into a single intelligent brain that drives ROI.

Responsibilities:
- Bridge opportunity scoring with security cycle triggers
- Feed back learned knowledge to improve pipeline operations
- Emit real-time alerts and autonomous actions
- Maintain unified context and decision history

Exports:
- IntegrationOrchestrator
- get_orchestrator() -> singleton
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.cycles.knowledge_capture import KnowledgeCapture
from core.opportunity.scoring import FeedbackOutcome, get_engine

logger = logging.getLogger("orion.integration_orchestrator")


@dataclass
class IntegrationEvent:
    """A cross-phase event that drives system intelligence."""

    id: str
    source: str  # opportunity_engine, security_cycle, mission_control
    target: str  # security_cycle, mission_control, opportunity_engine
    type: str
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: int = 5

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority,
        }


class IntegrationOrchestrator:
    """Transparent brain of Rastro: coordinates FASE 1-3 continuously."""

    def __init__(self) -> None:
        self.knowledge = KnowledgeCapture()
        self.engine = get_engine()
        self._last_opportunity_analysis = None
        self._security_alert_sockets = []

    def start(self) -> None:
        logger.info("Integration Orchestrator started")
        # create watches for key phases
        self.watch_opportunity_engine()
        self.watch_security_cycle()

    def watch_opportunity_engine(self) -> None:
        """Listen for top opportunity changes → trigger validation and report generation."""
        pass

    def watch_security_cycle(self) -> None:
        """Watch for security cycle events, adjust opportunity priorities."""
        pass

    def emit_event(
        self, source: str, target: str, type_: str, payload: dict[str, Any], priority: int = 5
    ) -> IntegrationEvent:
        event = IntegrationEvent(
            id=f"{source}_{type_}_{datetime.now().timestamp()}",
            source=source,
            target=target,
            type=type_,
            payload=payload,
            priority=priority,
        )
        logger.info("Integration event: %s -> %s | %s", source, target, type_)
        self._handle_event(event)
        return event

    def _handle_event(self, event: IntegrationEvent) -> None:
        if event.target == "security_cycle":
            self._route_to_security_cycle(event)
        elif event.target == "mission_control":
            self._route_to_mission_control(event)
        elif event.target == "opportunity_engine":
            self._route_to_opportunity_engine(event)

    def _route_to_security_cycle(self, event: IntegrationEvent) -> None:
        logger.info("[SECURITY_CYCLE] Route event: %s", event.type)

    def _route_to_mission_control(self, event: IntegrationEvent) -> None:
        logger.info("[MISSION_CONTROL] Dashboard update event: %s", event.type)

    def _route_to_opportunity_engine(self, event: IntegrationEvent) -> None:
        if event.type == "security_finding_confirmed":
            finding_id = event.payload.get("finding_id")
            if finding_id:
                self.engine.record_feedback(finding_id, FeedbackOutcome.ACCEPT)
                logger.info("[OPPORTUNITY_ENGINE] Added security learning: finding %s", finding_id)

    def run_cycle(self) -> dict[str, Any]:
        """One full orchestration cycle: scan → score → trigger → learn -> integrate.

        Returns unified status snapshot.
        """
        latest_knowledge = list(self.knowledge.get_entries(limit=10))

        opportunities = self.engine.compute_opportunities(limit=20)

        high_value_opportunities = [o for o in opportunities if o.final_score > 500]
        for opp in high_value_opportunities:
            self.emit_event(
                source="opportunity_engine",
                target="security_cycle",
                type_="opportunity_high_value",
                payload={"finding_id": opp.opportunity_id, "score": opp.final_score, "domain": opp.title},
                priority=8,
            )

        context = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "knowledge_count": len(latest_knowledge),
            "opportunities_analyzed": len(opportunities),
            "high_value_opportunities": len(high_value_opportunities),
            "domains_affected": list({opp.title for opp in opportunities}),
        }

        logger.info("Integration cycle complete: analyzed %d opportunities", len(opportunities))
        return {"status": "ok", "integration": context}

    def get_health(self) -> dict[str, Any]:
        return {
            "orchestrator": "active",
            "knowledge_entries": len(self.knowledge.get_entries()),
            "opportunity_sources": len(self.engine.get_top5_by_domain()),
            "last_cycle": datetime.now(timezone.utc).isoformat(),
        }


_ENGINE: IntegrationOrchestrator | None = None


def get_orchestrator() -> IntegrationOrchestrator:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = IntegrationOrchestrator()
        _ENGINE.start()
    return _ENGINE
