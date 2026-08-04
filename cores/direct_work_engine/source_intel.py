"""Source Intelligence — Platform Analysis System for the Universal Opportunity Discovery Engine.

Bridges the curated global source database (``cores/opportunity/global_sources``,
100+ pre-verified platforms) into the Direct Work Engine so the user can ask
OWNEX the spec question — "where does my next hour convert best?".

For every source it produces a `PlatformAnalysis`: Argentina compatibility,
payment method, average reward, entry barrier, task transparency, trust score,
earning potential and an OWNEX recommendation. It also reports uncovered DWE
categories so the knowledge base can keep expanding (Continuous Expansion).

Reuses the curated quality_score/priority/instance flags — never invents gold
scores. Import of the source database is lazy to keep DWE decoupled.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("ownex.direct_work_engine.source_intel")

# Payment channels OWNEX can actually collect through from Argentina are the
# low-friction ones (profile/email/API/chat). Anything else → "varies".
_LOW_FRICTION_METHODS = frozenset({"profile_only", "profile_email", "direct_message", "api"})

# Source shapes that expose objective, public work (high transparency).
_HIGH_TRANSPARENCY_TYPES = frozenset({"platform", "direct_api", "aggregator"})


@dataclass(slots=True)
class PlatformAnalysis:
    """The full analysis card for a single opportunity source."""

    name: str
    url: str
    category: str
    source_type: str
    country_availability: str
    argentina_compatibility: str  # YES | NO | UNKNOWN
    argentina_reason: str
    payment_method: str
    average_reward: str
    entry_barrier: str  # LOW | MEDIUM | HIGH
    interview_required: bool
    portfolio_required: bool
    experience_required: bool
    task_transparency: float  # 0.0-1.0
    trust_score: float  # 0-100
    earning_potential: str  # LOW | MEDIUM | HIGH | VERY_HIGH
    recommendation: str  # DISCOVER | CONSIDER | AVOID
    priority: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "category": self.category,
            "source_type": self.source_type,
            "country_availability": self.country_availability,
            "argentina_compatibility": self.argentina_compatibility,
            "argentina_reason": self.argentina_reason,
            "payment_method": self.payment_method,
            "average_reward": self.average_reward,
            "entry_barrier": self.entry_barrier,
            "interview_required": self.interview_required,
            "portfolio_required": self.portfolio_required,
            "experience_required": self.experience_required,
            "task_transparency": round(self.task_transparency, 2),
            "trust_score": round(self.trust_score, 1),
            "earning_potential": self.earning_potential,
            "recommendation": self.recommendation,
            "priority": self.priority,
        }


class SourceIntelEngine:
    """Analyzes the curated global source database into actionable platform cards."""

    def analyze(
        self,
        categories: list[str] | None = None,
        query: str | None = None,
        min_trust: float | None = None,
    ) -> dict[str, Any]:
        sources = self._curated_sources()
        if categories:
            sources = [s for s in sources if s.category.value in categories]
        if query:
            needle = query.strip().lower()
            sources = [s for s in sources if needle in s.name.lower() or needle in (s.url or "").lower()]

        analyses = [self._analyze_source(s) for s in sources]
        if min_trust is not None:
            analyses = [a for a in analyses if a.trust_score >= min_trust]

        analyses.sort(key=lambda a: (a.recommendation == "DISCOVER", a.trust_score, a.priority), reverse=True)
        stats = self._stats(analyses)
        return {
            "analyzed": len(analyses),
            "total_curated_sources": len(self._curated_sources()),
            "stats": stats,
            "uncovered_categories": self._uncovered_categories(),
            "sources": [a.to_dict() for a in analyses],
        }

    @staticmethod
    def _curated_sources() -> list[Any]:
        """Lazy import keeps the DWE decoupled from the legacy curation module."""
        from cores.opportunity.global_sources import get_sources  # type: ignore[import-not-found]

        return get_sources()

    @staticmethod
    def _value(obj: Any, name: str, default: Any) -> Any:
        return getattr(obj, name, default)

    def _analyze_source(self, source: Any) -> PlatformAnalysis:
        quality = float(self._value(source, "quality_score", 0.5))
        priority = int(self._value(source, "priority", 0))
        interview = bool(self._value(source, "requires_interview", False))
        portfolio = bool(self._value(source, "requires_portfolio", False))
        experience = bool(self._value(source, "requires_experience", False))
        method = str(self._value(source, "apply_method", "profile_only"))
        source_type = str(self._value(source, "type", "platform"))
        region = str(self._value(source, "region", "global"))
        payout = str(self._value(source, "estimated_payout_range", "varies"))

        barrier_flags = sum([interview, portfolio, experience])
        entry_barrier = "LOW" if barrier_flags == 0 else ("MEDIUM" if barrier_flags <= 1 else "HIGH")

        transparency = 1.0 if source_type in _HIGH_TRANSPARENCY_TYPES else (0.6 if source_type == "forum" else 0.4)

        trust_score = round(
            quality * 100
            - (10 if interview else 0)
            - (8 if portfolio else 0)
            - (8 if experience else 0)
            - (5 if source_type in ("job_board", "forum") else 0),
            1,
        )
        trust_score = max(5.0, min(98.0, trust_score))

        argentina, reason = self._argentina_compatibility(
            region=region,
            method=method,
            source_type=source_type,
            interview=interview,
            portfolio=portfolio,
            experience=experience,
        )

        earning = self._earning_potential(quality, priority, barrier_flags)
        recommendation = self._recommendation(trust_score, argentina, barrier_flags, source_type)

        payment_label = "profile/email/API" if method in _LOW_FRICTION_METHODS else method
        return PlatformAnalysis(
            name=str(self._value(source, "name", "?")),
            url=str(self._value(source, "url", "")),
            category=self._value(source, "category", "").value
            if hasattr(self._value(source, "category", ""), "value")
            else str(self._value(source, "category", "")),
            source_type=source_type,
            country_availability="global" if region == "global" else region,
            argentina_compatibility=argentina,
            argentina_reason=reason,
            payment_method=payment_label,
            average_reward=payout,
            entry_barrier=entry_barrier,
            interview_required=interview,
            portfolio_required=portfolio,
            experience_required=experience,
            task_transparency=transparency,
            trust_score=trust_score,
            earning_potential=earning,
            recommendation=recommendation,
            priority=priority,
        )

    def _argentina_compatibility(
        self,
        region: str,
        method: str,
        source_type: str,
        interview: bool,
        portfolio: bool,
        experience: bool,
    ) -> tuple[str, str]:
        if region == "global" and method in _LOW_FRICTION_METHODS and not (interview or portfolio or experience):
            return "YES", "Global, remote, low-friction signup — accesible desde Argentina."
        if region == "global" and source_type in ("platform", "direct_api", "aggregator"):
            return "YES", "Global platform sin restricción geográfica publicada."
        if region != "global":
            return "UNKNOWN", f"Región declarada '{region}' — verificar disponibilidad para Argentina."
        return "UNKNOWN", "No hay datos suficientes en la fuente curada."

    @staticmethod
    def _earning_potential(quality: float, priority: int, barrier_flags: int) -> str:
        raw = quality * 10 + priority * 0.8 - barrier_flags * 1.2
        if raw >= 16:
            return "VERY_HIGH"
        if raw >= 12:
            return "HIGH"
        if raw >= 8:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _recommendation(trust: float, argentina: str, barrier_flags: int, source_type: str) -> str:
        if trust >= 70 and argentina == "YES" and barrier_flags == 0:
            return "DISCOVER"
        if trust >= 50 and barrier_flags <= 1:
            return "CONSIDER"
        if trust < 40 or barrier_flags >= 3 or source_type == "job_board":
            return "AVOID"
        return "CONSIDER"

    @staticmethod
    def _stats(analyses: list[PlatformAnalysis]) -> dict[str, Any]:
        by_category: dict[str, int] = {}
        for a in analyses:
            by_category[a.category] = by_category.get(a.category, 0) + 1
        by_recommendation: dict[str, int] = {}
        for a in analyses:
            by_recommendation[a.recommendation] = by_recommendation.get(a.recommendation, 0) + 1
        return {
            "by_category": by_category,
            "by_recommendation": by_recommendation,
            "argentina_compatible": sum(1 for a in analyses if a.argentina_compatibility == "YES"),
            "avg_trust_score": round(sum(a.trust_score for a in analyses) / len(analyses), 1) if analyses else 0.0,
        }

    @staticmethod
    def _uncovered_categories() -> list[str]:
        """DWE categories with no curated source yet — candidates for expansion."""
        from cores.direct_work_engine.models import OpportunityCategory

        engine = SourceIntelEngine()
        covered = {engine._analyze_source(s).category for s in engine._curated_sources()}
        return sorted(c.value for c in OpportunityCategory if c.value not in covered)
