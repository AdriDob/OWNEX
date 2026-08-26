"""Income Diversification Engine — analyzes income concentration and recommends diversification."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.capital.diversification")


@dataclass
class DiversificationRecommendation:
    action: str
    priority: str
    rationale: str
    estimated_impact: float = 0.0
    effort: str = "medium"
    timeline: str = "3-6 months"


@dataclass
class DiversificationAnalysis:
    total_sources: int
    top_source_pct: float
    top_3_pct: float
    hhi: float  # Herfindahl-Hirschman Index
    by_source: dict[str, dict[str, Any]] = field(default_factory=dict)
    recommendations: list[DiversificationRecommendation] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class DiversificationEngine:
    """Analyzes income concentration and recommends diversification strategies."""

    def __init__(self) -> None:
        pass

    def analyze(
        self,
        income_sources: list[dict] | None = None,
        platform_exposure: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Analyze income diversification."""
        income_sources = income_sources or []
        platform_exposure = platform_exposure or {}

        # If no sources provided, try to get from truth layer
        if not income_sources and not platform_exposure:
            income_sources = self._get_income_sources_from_truth()

        # Calculate metrics
        total_income = sum(s.get("amount", 0) for s in income_sources)
        by_source = {}
        for s in income_sources:
            amount = s.get("amount", 0)
            pct = (amount / total_income * 100) if total_income > 0 else 0
            by_source[s.get("name", s.get("id", "unknown"))] = {
                "amount": amount,
                "pct": round(pct, 1),
                "platform": s.get("platform", "unknown"),
            }

        # Calculate HHI
        hhi = sum((pct / 100) ** 2 for pct in [v["pct"] for v in by_source.values()])

        # Top source and top 3
        sorted_sources = sorted(by_source.items(), key=lambda x: x[1]["amount"], reverse=True)
        top_source_pct = sorted_sources[0][1]["pct"] if sorted_sources else 0
        top_3_pct = sum(v["pct"] for _, v in sorted_sources[:3])

        # Generate recommendations
        recommendations = self._generate_recommendations(total_income, by_source, top_source_pct, top_3_pct, hhi)

        return DiversificationAnalysis(
            total_sources=len(income_sources),
            top_source_pct=round(top_source_pct, 1),
            top_3_pct=round(top_3_pct, 1),
            hhi=round(hhi, 4),
            by_source={k: v for k, v in by_source.items()},
            recommendations=recs,
            timestamp=datetime.now(UTC).isoformat(),
        ).__dict__

    def _get_income_sources_from_truth(self) -> list[dict]:
        """Get income sources from truth layer."""
        try:
            from cores.financial.truth_layer import get_truth_layer

            truth = get_truth_layer()
            state = truth.get_state()
            sources = []
            for pid, ps in state.by_platform.items():
                if ps.verified_balance > 0 or ps.pending_balance > 0:
                    sources.append(
                        {
                            "name": pid,
                            "platform": pid,
                            "amount": ps.verified_balance + ps.pending_balance,
                        }
                    )
            return sources
        except Exception:
            return []

        def _generate_recommendations(
            self,
            total_income: float,
            by_source: dict[str, dict],
            top_source_pct: float,
            top_3_pct: float,
            hhi: float,
        ) -> list[DiversificationRecommendation]:
            """Generate diversification recommendations."""
            recs: list[DiversificationRecommendation] = []

            # High concentration
            if top_source_pct > 60:
                recs.append(
                    DiversificationRecommendation(
                        action=f"Reducir dependencia de {max(by_source.items(), key=lambda x: x[1]['amount'])[0] if by_source else 'fuente principal'}",
                        priority="high",
                        rationale=f"Top fuente representa {top_source_pct:.1f}% de ingresos — riesgo de concentración crítico",
                        estimated_impact=total_income * 0.2,
                        effort="high",
                        timeline="6-12 months",
                    )
                )

            if top_source_pct > 30:
                recs.append(
                    DiversificationRecommendation(
                        action="Desarrollar 2da y 3ra fuente de ingreso",
                        priority="high",
                        rationale=f"Top fuente = {top_source_pct:.1f}% — riesgo de concentración alto",
                        estimated_impact=total_income * 0.15,
                        effort="high",
                        timeline="6-12 months",
                    )
                )

            if top_3_pct > 80:
                recs.append(
                    DiversificationRecommendation(
                        action="Expandir a nuevas plataformas/categorías",
                        priority="medium",
                        rationale=f"Top 3 = {top_3_pct:.1f}% — vulnerabilidad sistémica",
                        estimated_impact=total_income * 0.1,
                        effort="medium",
                        timeline="3-6 months",
                    )
                )

            if hhi > 0.25:
                recs.append(
                    DiversificationRecommendation(
                        action="Redistribuir ingresos hacia fuentes menores",
                        priority="medium",
                        rationale=f"HHI={hhi:.3f} — concentración alta (umbral 0.25)",
                        estimated_impact=total_income * 0.1,
                        effort="medium",
                        timeline="3-9 months",
                    )
                )

            # Platform-specific recommendations
            if by_source:
                for name, data in by_source.items():
                    if data["pct"] > 40:
                        recs.append(
                            DiversificationRecommendation(
                                action=f"Reducir dependencia de {name}",
                                priority="high",
                                rationale=f"{name} = {data['pct']:.1f}% de ingresos",
                                estimated_impact=total_income * 0.1,
                                effort="high",
                                timeline="6-12 months",
                            )
                        )

            # Low total income
            if total_income < 1000:
                recs.append(
                    DiversificationRecommendation(
                        action="Acelerar First-Day Guide + Work Bank",
                        priority="high",
                        rationale=f"Ingresos totales bajos (${total_income:.0f}) — priorizar cash flow inmediato",
                        estimated_impact=5000,
                        effort="high",
                        timeline="1-3 months",
                    )
                )

            return recs


_diversification_engine: DiversificationEngine | None = None


def get_diversification_engine() -> DiversificationEngine:
    global _diversification_engine
    if _diversification_engine is None:
        _diversification_engine = DiversificationEngine()
    return _diversification_engine
