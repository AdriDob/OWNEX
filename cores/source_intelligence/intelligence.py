"""Source Intelligence — Prioritization, ranking, and renewal decisions.

This module implements the "Source Intelligence" layer that:
- Ranks sources by priority and expected value
- Determines which sources to renew vs retire
- Generates intelligence reports for the user
- Handles automatic renewal scheduling
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .verifier import SourceVerdict


class SourcePriority(Enum):
    """Priority level for a source."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    RETIRE = "retire"


@dataclass
class IntelligenceReport:
    """Intelligence report with source rankings and recommendations."""

    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    period: str = "weekly"

    # Summary statistics
    total_sources: int = 0
    active_sources: int = 0
    fully_eligible: int = 0
    partial_eligible: int = 0
    ineligible: int = 0
    retired: int = 0

    # Priority rankings
    critical_sources: list[str] = field(default_factory=list)
    high_priority: list[str] = field(default_factory=list)
    monitoring: list[str] = field(default_factory=list)
    retire_list: list[str] = field(default_factory=list)

    # Detailed verdicts per source
    source_verdicts: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Recommendations
    actions: list[str] = field(default_factory=list)
    emerging_opportunities: list[str] = field(default_factory=list)
    declining_sources: list[str] = field(default_factory=list)


@dataclass
class PriorityRanking:
    """Ranking of sources for attention."""

    source_id: str
    source_name: str
    overall_score: float
    priority: SourcePriority
    reason: str
    recommended_action: str
    expected_ev_per_hour: float = 0.0


class SourceIntelligence:
    """Core intelligence engine for source management."""

    def __init__(self, verifier, registry, payment_engine):
        self.verifier = verifier
        self.registry = registry
        self.payment_engine = payment_engine
        self.rankings: dict[str, PriorityRanking] = {}

    def generate_report(self, period: str = "weekly") -> IntelligenceReport:
        """Generate an intelligence report for the given period."""
        from datetime import datetime

        now = datetime.now()
        report = IntelligenceReport(
            generated_at=now.isoformat(),
            period=period,
            total_sources=len(self.registry.all_sources()),
        )

        sources = self.registry.all_sources()
        report.active_sources = len(self.registry.active_sources())

        # Run verification on all sources that need it
        stale_sources = self.verifier.verify_all_stale()

        # Build verdicts dict
        verdicts = {}
        fully_eligible_count = 0
        partial_eligible_count = 0
        ineligible_count = 0
        retired_count = 0

        for pipeline_result in stale_sources:
            verdict = pipeline_result.verdict
            verdicts[pipeline_result.source_id] = self._verdict_to_dict(verdict)

            if verdict.fully_eligible:
                fully_eligible_count += 1
            elif verdict.recommendation == "partial":
                partial_eligible_count += 1
            elif verdict.recommendation == "ineligible":
                ineligible_count += 1
            else:
                retired_count += 1

        report.fully_eligible = fully_eligible_count
        report.partial_eligible = partial_eligible_count
        report.ineligible = ineligible_count
        report.retired = retired_count

        # Generate priority rankings for ALL sources
        self._generate_rankings(sources, verdicts)

        # Sort rankings by priority
        all_rankings = list(self.rankings.values())
        all_rankings.sort(key=lambda r: (-r.overall_score, r.priority.value))

        # Categorize by priority
        for ranking in all_rankings:
            if ranking.priority == SourcePriority.CRITICAL:
                report.critical_sources.append(ranking.source_id)
            elif ranking.priority == SourcePriority.HIGH:
                report.high_priority.append(ranking.source_id)
            elif ranking.priority == SourcePriority.MEDIUM:
                report.monitoring.append(ranking.source_id)
            elif ranking.priority == SourcePriority.LOW or ranking.priority == SourcePriority.RETIRE:
                report.retire_list.append(ranking.source_id)

        # Generate actions
        report.actions = self._generate_actions(verdicts, fully_eligible_count, ineligible_count)

        # Identify emerging opportunities
        report.emerging_opportunities = self._identify_emerging(sources, verdicts)

        # Identify declining sources
        report.declining_sources = self._identify_declining(sources, verdicts)

        return report

    def _verdict_to_dict(self, verdict: SourceVerdict) -> dict[str, Any]:
        """Convert a SourceVerdict to a dictionary for reporting."""
        return {
            "source_id": verdict.source_id,
            "fully_eligible": verdict.fully_eligible,
            "overall_score": verdict.overall_score,
            "eligibility_score": verdict.eligibility_score,
            "integration_score": verdict.integration_score,
            "payout_score": verdict.payout_score,
            "recommendation": verdict.recommendation,
            "eligible_reasons": verdict.eligible_reasons,
            "ineligibility_reasons": verdict.ineligibility_reasons,
        }

    def _generate_rankings(self, sources: list, verdicts: dict[str, dict]) -> None:
        """Generate priority rankings for all sources."""
        self.rankings = {}

        for source in sources:
            source_id = source.source_id

            # Get verdict if available, otherwise create default
            if source_id in verdicts:
                verdict_data = verdicts[source_id]
                overall_score = verdict_data.get("overall_score", 0.0)
                verdict_data.get("recommendation", "ineligible")
                eligible_reasons = verdict_data.get("eligible_reasons", [])
                ineligibility_reasons = verdict_data.get("ineligibility_reasons", [])
            else:
                # Source hasn't been verified yet
                overall_score = source.verification_score
                eligible_reasons = []
                ineligibility_reasons = ["Sin verificar aún"]

            # Determine priority based on score and eligibility
            if overall_score >= 80 and any("Elegibilidad desde Argentina" in r for r in eligible_reasons):
                priority = SourcePriority.CRITICAL
                reason = "Alta valoración y totalmente elegible AR"
                recommended_action = "pursue"
            elif overall_score >= 80:
                priority = SourcePriority.CRITICAL
                reason = "Alta valoración"
                recommended_action = "pursue"
            elif overall_score >= 60:
                priority = SourcePriority.HIGH
                reason = "Buena valoración, verificar elegibilidad completa"
                recommended_action = "pursue"
            elif overall_score >= 40:
                priority = SourcePriority.MEDIUM
                reason = "Valoración moderada, requiere monitoreo"
                recommended_action = "monitor"
            elif overall_score > 0:
                priority = SourcePriority.LOW
                reason = "Baja valoración, revisar viabilidad"
                recommended_action = "investigate"
            else:
                priority = SourcePriority.RETIRE
                reason = "Sin valor verificado, candidata a retirar"
                recommended_action = "retire"

            # Adjust based on eligibility
            has_ar_eligibility = any("Elegibilidad desde Argentina" in r for r in eligible_reasons + ineligibility_reasons)
            if not has_ar_eligibility and priority == SourcePriority.CRITICAL:
                priority = SourcePriority.HIGH
                reason += " - problema de elegibilidad AR"
            elif not has_ar_eligibility and priority == SourcePriority.HIGH:
                priority = SourcePriority.MEDIUM
                reason += " - problema de elegibilidad AR"

            self.rankings[source_id] = PriorityRanking(
                source_id=source_id,
                source_name=source.name if hasattr(source, "name") else source_id,
                overall_score=overall_score,
                priority=priority,
                reason=reason,
                recommended_action=recommended_action,
                expected_ev_per_hour=self._estimate_ev_per_hour(source),
            )

    def _estimate_ev_per_hour(self, source) -> float:
        """Estimate expected value per hour of work from this source."""
        avg_payout = getattr(source, "avg_payout_usd", 0) or 0
        avg_time = getattr(source, "avg_time_to_payout_days", 30) or 30

        if avg_payout > 0 and avg_time > 0:
            ev_per_day = avg_payout / max(avg_time, 1)
            ev_per_hour = round(ev_per_day / 8, 2)
            return ev_per_hour
        return 0.0

    def _generate_actions(self, verdicts: dict[str, dict], fully_eligible: int, ineligible: int) -> list[str]:
        """Generate recommended actions based on verdicts."""
        actions = []

        if fully_eligible > 0:
            actions.append(f"{fully_eligible} source(s) totalmente elegible - priorizar para ejecución")

        if ineligible > 0:
            actions.append(f"{ineligible} source(s) no elegible - considerar retirar o investigar")

        # Check for sources that need renewal
        stale_count = len(self.verifier.verify_all_stale())
        if stale_count > 0:
            actions.append(f"Renovar verificación de {stale_count} source(s) stale")

        # Emerging opportunities
        actions.append("Investigar nuevas sources que aparecen en el intelligence report")

        return actions

    def _identify_emerging(self, sources, verdicts) -> list[str]:
        """Identify emerging opportunities - new or recently verified high-value sources."""
        emerging = []
        for source in sources:
            score = source.verification_score
            if score >= 70 and source.last_verified:
                from datetime import datetime, timedelta

                last = datetime.fromisoformat(source.last_verified)
                if datetime.now() - last < timedelta(days=7):
                    emerging.append(source.source_id)
        return emerging

    def _identify_declining(self, sources, verdicts) -> list[str]:
        """Identify declining sources - previously good but now losing value."""
        declining = []
        for source in sources:
            score = source.verification_score
            if score < 40 and source.last_verified:
                from datetime import datetime, timedelta

                last = datetime.fromisoformat(source.last_verified)
                if datetime.now() - last > timedelta(days=30):
                    declining.append(source.source_id)
        return declining
