"""Opportunity Scorer — evalúa oportunidades con scoring multi-factor (0-100)."""

from __future__ import annotations

import logging
from uuid import uuid4

from core.market_intelligence.models import (
    Confidence,
    MarketDomain,
    OpportunityAssessment,
    OpportunityScore,
    SignalType,
    SourceSignal,
    SourceTier,
)

logger = logging.getLogger("orion.intel.scorer")


class OpportunityScorer:
    """Multi-factor opportunity scoring engine."""

    def score_signal(self, signal: SourceSignal) -> OpportunityAssessment:
        """Score a signal as an opportunity."""
        score = self._compute_score(signal)
        confidence = self._to_confidence(score.overall)
        strengths, risks = self._assess(signal, score)

        return OpportunityAssessment(
            id=str(uuid4()),
            title=signal.title,
            domain=signal.domain,
            signal_id=signal.id,
            source_id=signal.source_id,
            category=self._categorize(signal),
            description=signal.body[:300],
            strengths=strengths,
            risks=risks,
            score=score,
            recommended_action=self._recommend(score, signal),
            confidence=confidence,
            tags=[signal.signal_type.value, signal.domain.value, signal.source_tier.value],
        )

    def _compute_score(self, signal: SourceSignal) -> OpportunityScore:
        """Compute all score dimensions."""
        s = OpportunityScore()

        # Source quality (0-100): tier A=90, B=60, C=20
        tier_map = {SourceTier.A: 90, SourceTier.B: 60, SourceTier.C: 20}
        s.source_quality = tier_map.get(signal.source_tier, 50)
        # Adjust for manipulation flags
        flag_penalty = len(signal.manipulation_flags) * 10
        s.source_quality = max(0, s.source_quality - flag_penalty)

        # Evidence quality (0-100): based on signal type
        evidence_map = {
            SignalType.FUNDAMENTAL: 80,
            SignalType.TECHNICAL_SETUP: 65,
            SignalType.NEWS_EVENT: 55,
            SignalType.SCAM_ALERT: 75,
            SignalType.RISK_WARNING: 70,
            SignalType.OPPORTUNITY: 40,
            SignalType.MARKET_SENTIMENT: 30,
            SignalType.PROMOTION: 10,
            SignalType.GENERAL_DISCUSSION: 20,
            SignalType.NOISE: 5,
        }
        s.evidence = evidence_map.get(signal.signal_type, 30)

        # Risk assessment (inverse: higher = safer)
        risk_map = {
            SignalType.SCAM_ALERT: 90,
            SignalType.RISK_WARNING: 85,
            SignalType.FUNDAMENTAL: 60,
            SignalType.TECHNICAL_SETUP: 50,
            SignalType.NEWS_EVENT: 55,
            SignalType.MARKET_SENTIMENT: 45,
            SignalType.OPPORTUNITY: 30,
            SignalType.PROMOTION: 10,
        }
        s.risk = risk_map.get(signal.signal_type, 50)

        # Potential return
        return_map = {
            SignalType.OPPORTUNITY: 75,
            SignalType.TECHNICAL_SETUP: 60,
            SignalType.FUNDAMENTAL: 55,
            SignalType.NEWS_EVENT: 45,
            SignalType.MARKET_SENTIMENT: 35,
            SignalType.SCAM_ALERT: 10,
            SignalType.RISK_WARNING: 10,
            SignalType.PROMOTION: 5,
        }
        s.potential_return = return_map.get(signal.signal_type, 30)

        # Difficulty (inverse: higher = easier)
        diff_map = {
            SignalType.MARKET_SENTIMENT: 70,
            SignalType.NEWS_EVENT: 65,
            SignalType.SCAM_ALERT: 60,
            SignalType.RISK_WARNING: 60,
            SignalType.TECHNICAL_SETUP: 50,
            SignalType.FUNDAMENTAL: 45,
            SignalType.OPPORTUNITY: 35,
            SignalType.PROMOTION: 80,
        }
        s.difficulty = diff_map.get(signal.signal_type, 50)

        # Competition (inverse: higher = less competition)
        competition_map = {
            MarketDomain.MEMECOIN: 20,
            MarketDomain.CRYPTO: 35,
            MarketDomain.DEFI: 40,
            MarketDomain.NFT: 45,
            MarketDomain.AI_CRYPTO: 55,
            MarketDomain.GAMING: 50,
            MarketDomain.INFRASTRUCTURE: 60,
        }
        s.competition = competition_map.get(signal.domain, 40)

        # Timing
        urgency_map = {"critical": 80, "high": 65, "normal": 40, "low": 20}
        s.timing = urgency_map.get(signal.urgency, 40)

        # Overall weighted score
        s.overall = (
            s.source_quality * 0.20
            + s.evidence * 0.18
            + s.risk * 0.15
            + s.potential_return * 0.17
            + s.difficulty * 0.10
            + s.competition * 0.10
            + s.timing * 0.10
        )

        # Confidence = how consistent the signal is
        dimensions = [s.source_quality, s.evidence, s.risk, s.potential_return]
        s.confidence = sum(dimensions) / len(dimensions)

        return s

    def _to_confidence(self, score: float) -> Confidence:
        if score >= 70:
            return Confidence.HIGH
        if score >= 45:
            return Confidence.MEDIUM
        if score >= 25:
            return Confidence.LOW
        return Confidence.VERY_LOW

    def _categorize(self, signal: SourceSignal) -> str:
        if signal.domain == MarketDomain.BUG_BOUNTY:
            return "bounty"
        if signal.signal_type in (SignalType.TECHNICAL_SETUP, SignalType.MARKET_SENTIMENT):
            return "trading"
        if signal.signal_type in (SignalType.FUNDAMENTAL, SignalType.OPPORTUNITY):
            return "investment"
        return "research"

    def _assess(self, signal: SourceSignal, score: OpportunityScore) -> tuple[list[str], list[str]]:
        strengths: list[str] = []
        risks: list[str] = []

        if score.source_quality >= 70:
            strengths.append("Fuente confiable con historial comprobado")
        if score.evidence >= 60:
            strengths.append("Señal respaldada por fundamentos o datos")
        if score.potential_return >= 60:
            strengths.append("Alto potencial de retorno")
        if score.timing >= 60:
            strengths.append("Buen momento de mercado")

        if score.risk < 40:
            risks.append("Alto riesgo — señal especulativa")
        if score.source_quality < 40:
            risks.append("Fuente de baja confiabilidad")
        if len(signal.manipulation_flags) >= 2:
            risks.append("Múltiples indicadores de manipulación detectados")
        if signal.signal_type == SignalType.PROMOTION:
            risks.append("Contenido promocional — verificar independencia")

        return strengths, risks

    def _recommend(self, score: OpportunityScore, signal: SourceSignal) -> str:
        if score.overall >= 75:
            return "Prioridad alta — investigar y considerar acción inmediata"
        if score.overall >= 55:
            return "Monitorear — añadir a lista de seguimiento"
        if score.overall >= 35:
            return "Info útil pero no urgente — revisar en próximo briefing"
        return "Baja prioridad — archivar o ignorar"


_OPPORTUNITY_SCORER: OpportunityScorer | None = None


def get_opportunity_scorer() -> OpportunityScorer:
    global _OPPORTUNITY_SCORER
    if _OPPORTUNITY_SCORER is None:
        _OPPORTUNITY_SCORER = OpportunityScorer()
    return _OPPORTUNITY_SCORER
