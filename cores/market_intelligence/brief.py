"""Generación de briefing diario de inteligencia ORION."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.market_intelligence.memory import get_intel_memory
from core.market_intelligence.models import (
    IntelligenceBrief,
    IntelligenceSource,
    OpportunityAssessment,
    SourceSignal,
    SourceTier,
)
from core.market_intelligence.source_manager import get_source_manager

logger = logging.getLogger("orion.intel.brief")


def generate_brief(
    opportunities: list[OpportunityAssessment] | None = None,
    signals: list[SourceSignal] | None = None,
    sources: list[IntelligenceSource] | None = None,
) -> IntelligenceBrief:
    """Generate a daily intelligence briefing."""
    src_mgr = get_source_manager()
    memory = get_intel_memory()

    sources = sources or src_mgr.list()
    signals = signals or []
    opportunities = opportunities or []

    # Summary
    tier_a = len([s for s in sources if s.tier == SourceTier.A])
    tier_b = len([s for s in sources if s.tier == SourceTier.B])
    tier_c = len([s for s in sources if s.tier == SourceTier.C])
    high_score = len([o for o in opportunities if o.score.overall >= 70])
    med_score = len([o for o in opportunities if 45 <= o.score.overall < 70])

    summary = (
        f"Se monitorearon {len(sources)} fuentes ({tier_a}A/{tier_b}B/{tier_c}C). "
        f"Se analizaron {len(signals)} señales. "
        f"Se identificaron {len(opportunities)} oportunidades "
        f"({high_score} alta prioridad, {med_score} media prioridad)."
    )

    # Top opportunities
    sorted_opps = sorted(opportunities, key=lambda o: o.score.overall, reverse=True)

    # Risks
    risks = [o.description for o in sorted_opps if o.score.risk < 40][:5]

    # Trends
    trends: list[str] = []
    domains: dict[str, int] = {}
    signal_types: dict[str, int] = {}
    for s in signals:
        domains[s.domain.value] = domains.get(s.domain.value, 0) + 1
        signal_types[s.signal_type.value] = signal_types.get(s.signal_type.value, 0) + 1
    if domains:
        top_domain = max(domains, key=domains.get)
        trends.append(f"Dominio más activo: {top_domain} ({domains[top_domain]} señales)")
    for st, count in sorted(signal_types.items(), key=lambda x: -x[1])[:3]:
        trends.append(f"Señales {st}: {count}")

    # Learned from memory
    mem_stats = memory.stats()
    learned: list[str] = []
    if mem_stats["total_outcomes"] > 0:
        learned.append(
            f"Precisión histórica: {mem_stats['accuracy'] * 100:.0f}% "
            f"({mem_stats['correct']}/{mem_stats['total_outcomes']})"
        )
    if mem_stats["pending_predictions"] > 0:
        learned.append(f"{mem_stats['pending_predictions']} predicciones pendientes de verificar")

    # Top actions
    top_actions: list[str] = []
    for opp in sorted_opps[:3]:
        top_actions.append(f"{opp.title} — {opp.recommended_action}")

    brief = IntelligenceBrief(
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        summary=summary,
        top_opportunities=sorted_opps[:10],
        risks=risks,
        signals_analyzed=len(signals),
        sources_active=len(sources),
        trends=trends,
        learned=learned,
        top_actions=top_actions,
    )

    return brief
