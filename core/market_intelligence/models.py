"""Modelos de datos para inteligencia de mercado ORION."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# ── Enums ────────────────────────────────────────────────────────────────


class SourceTier(Enum):
    A = "a"  # Alta calidad: historial, análisis técnico, transparencia
    B = "b"  # Información útil: noticias rápidas, descubrimiento temprano
    C = "c"  # Alto ruido: FOMO, presión, señales sin explicación


class SignalType(Enum):
    MARKET_SENTIMENT = "market_sentiment"
    PROJECT_ANALYSIS = "project_analysis"
    TECHNICAL_SETUP = "technical_setup"
    FUNDAMENTAL = "fundamental"
    NEWS_EVENT = "news_event"
    SCAM_ALERT = "scam_alert"
    OPPORTUNITY = "opportunity"
    RISK_WARNING = "risk_warning"
    GENERAL_DISCUSSION = "general_discussion"
    PROMOTION = "promotion"
    NOISE = "noise"


class MarketDomain(Enum):
    CRYPTO = "crypto"
    DEFI = "defi"
    NFT = "nft"
    TRADING = "trading"
    MEMECOIN = "memecoin"
    AI_CRYPTO = "ai_crypto"
    GAMING = "gaming"
    INFRASTRUCTURE = "infrastructure"
    BUG_BOUNTY = "bug_bounty"
    GENERAL = "general"


class Sentiment(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class Confidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


# ── Data models ──────────────────────────────────────────────────────────


@dataclass
class IntelligenceSource:
    """A monitored intelligence source (Telegram channel, group, etc)."""

    id: str
    name: str
    source_type: str  # telegram_channel, telegram_group, twitter, rss, etc
    tier: SourceTier = SourceTier.B
    domain: MarketDomain = MarketDomain.CRYPTO
    tags: list[str] = field(default_factory=list)
    url: str = ""
    description: str = ""
    language: str = "en"
    member_count: int = 0
    signals_total: int = 0
    signals_correct: int = 0
    reliability: float = 0.5  # 0.0 - 1.0, starts neutral
    last_analyzed: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def accuracy(self) -> float:
        if self.signals_total == 0:
            return 0.0
        return self.signals_correct / self.signals_total


@dataclass
class SourceSignal:
    """A signal extracted from a single message / post."""

    id: str
    source_id: str
    source_name: str
    signal_type: SignalType
    domain: MarketDomain
    title: str
    body: str = ""
    raw_text: str = ""
    sentiment: Sentiment = Sentiment.UNKNOWN
    confidence: Confidence = Confidence.LOW
    urgency: str = "normal"  # low, normal, high, critical
    topics: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)  # mentioned projects, tokens, CVE, etc
    estimated_value: float = 0.0
    risk_score: float = 0.5  # 0.0 - 1.0
    manipulation_flags: list[str] = field(default_factory=list)
    posted_at: str = ""
    collected_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    source_tier: SourceTier = SourceTier.B
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OpportunityScore:
    """Multi-factor opportunity assessment (0-100)."""

    overall: float = 0.0
    source_quality: float = 0.0  # credibility of the source
    evidence: float = 0.0  # quality of supporting evidence
    risk: float = 0.0  # inverse: lower risk = higher score
    potential_return: float = 0.0  # expected upside
    difficulty: float = 0.0  # inverse: easier = higher score
    competition: float = 0.0  # inverse: less competition = higher score
    timing: float = 0.0  # market timing quality
    confidence: float = 0.0  # overall confidence in assessment

    def to_dict(self) -> dict[str, float]:
        return {
            "overall": round(self.overall, 1),
            "source_quality": round(self.source_quality, 1),
            "evidence": round(self.evidence, 1),
            "risk": round(self.risk, 1),
            "potential_return": round(self.potential_return, 1),
            "difficulty": round(self.difficulty, 1),
            "competition": round(self.competition, 1),
            "timing": round(self.timing, 1),
            "confidence": round(self.confidence, 1),
        }


@dataclass
class OpportunityAssessment:
    """A fully assessed market/bounty opportunity."""

    id: str
    title: str
    domain: MarketDomain
    signal_id: str = ""
    source_id: str = ""
    category: str = ""  # investment, trading, bounty, research
    description: str = ""
    strengths: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    score: OpportunityScore = field(default_factory=OpportunityScore)
    recommended_action: str = ""
    estimated_effort: str = ""  # minutes, hours, days
    estimated_value_usd: float = 0.0
    confidence: Confidence = Confidence.LOW
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_brief(self) -> str:
        lines = [
            f"🎯 *{self.title}*",
            f"Score: {self.score.overall:.0f}/100  |  Confianza: {self.confidence.value}",
        ]
        if self.strengths:
            lines.append("\n*Fortalezas:*")
            for s in self.strengths:
                lines.append(f"  + {s}")
        if self.risks:
            lines.append("\n*Riesgos:*")
            for r in self.risks:
                lines.append(f"  - {r}")
        if self.recommended_action:
            lines.append(f"\n→ {self.recommended_action}")
        return "\n".join(lines)


@dataclass
class IntelligenceBrief:
    """Daily intelligence briefing."""

    date: str = field(default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%d"))
    summary: str = ""
    top_opportunities: list[OpportunityAssessment] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    signals_analyzed: int = 0
    sources_active: int = 0
    trends: list[str] = field(default_factory=list)
    learned: list[str] = field(default_factory=list)
    top_actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_markdown(self, level: str = "summary") -> str:
        if level == "summary":
            lines = [
                f"📊 *ORION Intelligence Brief — {self.date}*",
                "",
                self.summary,
                "",
                f"📈 Señales: {self.signals_analyzed}  |  Fuentes: {self.sources_active}",
            ]
            if self.top_actions:
                lines.append("")
                lines.append("*Acciones recomendadas:*")
                for a in self.top_actions[:3]:
                    lines.append(f"  → {a}")
            return "\n".join(lines)

        lines = [
            f"📊 *ORION Intelligence Brief — {self.date}*",
            "",
            "## Resumen",
            self.summary,
            "",
            f"Señales analizadas: {self.signals_analyzed}  |  Fuentes activas: {self.sources_active}",
        ]
        if self.top_opportunities:
            lines.append("")
            lines.append("## Top oportunidades")
            for i, opp in enumerate(self.top_opportunities[:5], 1):
                lines.append(f"  {i}. {opp.to_brief()}")
        if self.risks:
            lines.append("")
            lines.append("## Riesgos")
            for r in self.risks:
                lines.append(f"  ⚠️ {r}")
        if self.trends:
            lines.append("")
            lines.append("## Tendencias detectadas")
            for t in self.trends:
                lines.append(f"  📈 {t}")
        if self.learned:
            lines.append("")
            lines.append("## Aprendizajes")
            for item in self.learned:
                lines.append(f"  📝 {item}")
        if self.top_actions:
            lines.append("")
            lines.append("## Acciones recomendadas")
            for a in self.top_actions:
                lines.append(f"  → {a}")
        return "\n".join(lines)
