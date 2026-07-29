"""Gestión de fuentes de inteligencia — registro, clasificación, credibilidad."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core.market_intelligence.models import Confidence, IntelligenceSource, MarketDomain, SourceTier

logger = logging.getLogger("orion.intel.source")


class SourceManager:
    """Registry and credibility tracker for intelligence sources."""

    def __init__(self) -> None:
        self._sources: dict[str, IntelligenceSource] = {}
        self._history: dict[str, list[dict[str, Any]]] = {}  # source_id -> outcome history

    # ── Registration ──

    def register(self, source: IntelligenceSource) -> IntelligenceSource:
        self._sources[source.id] = source
        if source.id not in self._history:
            self._history[source.id] = []
        logger.info("[INTEL] Source registered: %s (%s, tier=%s)", source.name, source.source_type, source.tier.value)
        return source

    def register_telegram(
        self,
        channel_id: str,
        name: str,
        tier: SourceTier | str = SourceTier.B,
        domain: MarketDomain | str = MarketDomain.CRYPTO,
        tags: list[str] | None = None,
        url: str = "",
        description: str = "",
    ) -> IntelligenceSource:
        if isinstance(tier, str):
            tier = SourceTier(tier)
        if isinstance(domain, str):
            domain = MarketDomain(domain)
        source = IntelligenceSource(
            id=f"tg_{channel_id}",
            name=name,
            source_type="telegram_channel",
            tier=tier,
            domain=domain,
            tags=tags or [],
            url=url,
            description=description,
        )
        return self.register(source)

    def unregister(self, source_id: str) -> bool:
        if source_id in self._sources:
            del self._sources[source_id]
            self._history.pop(source_id, None)
            return True
        return False

    # ── Access ──

    def get(self, source_id: str) -> IntelligenceSource | None:
        return self._sources.get(source_id)

    def list(self, tier: SourceTier | None = None, domain: MarketDomain | None = None) -> list[IntelligenceSource]:
        sources = list(self._sources.values())
        if tier:
            sources = [s for s in sources if s.tier == tier]
        if domain:
            sources = [s for s in sources if s.domain == domain]
        return sorted(sources, key=lambda s: s.reliability, reverse=True)

    def list_by_tier(self, tier: SourceTier) -> list[IntelligenceSource]:
        return self.list(tier=tier)

    # ── Credibility scoring ──

    def record_outcome(self, source_id: str, correct: bool, details: str = "") -> None:
        """Record whether a signal from this source was correct."""
        source = self._sources.get(source_id)
        if not source:
            logger.warning("[INTEL] Unknown source: %s", source_id)
            return
        source.signals_total += 1
        if correct:
            source.signals_correct += 1
        source.reliability = source.accuracy
        source.last_analyzed = datetime.now(timezone.utc).isoformat()
        self._history[source_id].append(
            {
                "correct": correct,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info(
            "[INTEL] Outcome recorded for %s: correct=%s (reliability now %.2f)",
            source.name,
            correct,
            source.reliability,
        )

    def get_reliability(self, source_id: str) -> float:
        source = self._sources.get(source_id)
        return source.reliability if source else 0.0

    def get_confidence(self, source_id: str) -> Confidence:
        rel = self.get_reliability(source_id)
        if rel >= 0.8:
            return Confidence.HIGH
        if rel >= 0.5:
            return Confidence.MEDIUM
        if rel >= 0.2:
            return Confidence.LOW
        return Confidence.VERY_LOW

    def get_correct_count(self, source_id: str) -> int:
        source = self._sources.get(source_id)
        return source.signals_correct if source else 0

    def get_total_count(self, source_id: str) -> int:
        source = self._sources.get(source_id)
        return source.signals_total if source else 0

    # ── Stats ──

    def stats(self) -> dict[str, Any]:
        tiers: dict[str, int] = {}
        domains: dict[str, int] = {}
        for s in self._sources.values():
            tiers[s.tier.value] = tiers.get(s.tier.value, 0) + 1
            domains[s.domain.value] = domains.get(s.domain.value, 0) + 1
        return {
            "total_sources": len(self._sources),
            "by_tier": tiers,
            "by_domain": domains,
            "total_signals_tracked": sum(s.signals_total for s in self._sources.values()),
            "total_correct": sum(s.signals_correct for s in self._sources.values()),
            "avg_reliability": round(
                sum(s.reliability for s in self._sources.values()) / max(len(self._sources), 1), 3
            ),
        }

    # ── Persistence placeholders ──

    def to_dict(self) -> dict[str, Any]:
        return {
            "sources": {k: v.__dict__ for k, v in self._sources.items()},
            "history": self._history,
        }


_SOURCE_MANAGER: SourceManager | None = None


def get_source_manager() -> SourceManager:
    global _SOURCE_MANAGER
    if _SOURCE_MANAGER is None:
        _SOURCE_MANAGER = SourceManager()
    return _SOURCE_MANAGER


def reset_source_manager() -> None:
    global _SOURCE_MANAGER
    _SOURCE_MANAGER = None
