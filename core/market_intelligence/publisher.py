"""EventBus publisher para inteligencia de mercado ORION."""

from __future__ import annotations

import logging

from core.market_intelligence.models import (
    IntelligenceBrief,
    IntelligenceSource,
    OpportunityAssessment,
    SourceSignal,
)

logger = logging.getLogger("orion.intel.publisher")


def publish_signal(signal: SourceSignal) -> None:
    """Publish a signal event to EventBus."""
    try:
        from cores.events.event_bus import get_event_bus

        bus = get_event_bus()
        bus.publish(
            "intel:signal:detected",
            {
                "id": signal.id,
                "source_id": signal.source_id,
                "source_name": signal.source_name,
                "signal_type": signal.signal_type.value,
                "domain": signal.domain.value,
                "title": signal.title,
                "sentiment": signal.sentiment.value,
                "confidence": signal.confidence.value,
                "urgency": signal.urgency,
                "entities": signal.entities,
                "manipulation_flags": signal.manipulation_flags,
            },
        )
    except Exception:
        logger.exception("[INTEL] Failed to publish signal event")


def publish_opportunity(opportunity: OpportunityAssessment) -> None:
    """Publish an assessed opportunity to EventBus."""
    try:
        from cores.events.event_bus import get_event_bus

        bus = get_event_bus()
        bus.publish(
            "intel:opportunity:assessed",
            {
                "id": opportunity.id,
                "title": opportunity.title,
                "domain": opportunity.domain.value,
                "score": opportunity.score.overall,
                "confidence": opportunity.confidence.value,
                "recommended_action": opportunity.recommended_action,
                "estimated_value_usd": opportunity.estimated_value_usd,
                "score_breakdown": opportunity.score.to_dict(),
            },
        )
    except Exception:
        logger.exception("[INTEL] Failed to publish opportunity event")


def publish_brief(brief: IntelligenceBrief) -> None:
    """Publish daily intelligence brief to EventBus."""
    try:
        from cores.events.event_bus import get_event_bus

        bus = get_event_bus()
        bus.publish(
            "intel:brief:generated",
            {
                "date": brief.date,
                "summary": brief.summary,
                "signals_analyzed": brief.signals_analyzed,
                "sources_active": brief.sources_active,
                "top_opportunities": len(brief.top_opportunities),
                "risks": len(brief.risks),
                "top_actions": brief.top_actions[:3],
            },
        )
    except Exception:
        logger.exception("[INTEL] Failed to publish brief event")


def publish_source_update(source: IntelligenceSource) -> None:
    """Publish source credibility update to EventBus."""
    try:
        from cores.events.event_bus import get_event_bus

        bus = get_event_bus()
        bus.publish(
            "intel:source:updated",
            {
                "id": source.id,
                "name": source.name,
                "tier": source.tier.value,
                "reliability": round(source.reliability, 3),
                "signals_total": source.signals_total,
                "signals_correct": source.signals_correct,
            },
        )
    except Exception:
        logger.exception("[INTEL] Failed to publish source update")
