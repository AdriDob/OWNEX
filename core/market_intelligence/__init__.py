"""ORION Market Intelligence — análisis de fuentes externas, señales y oportunidades."""

from __future__ import annotations

from core.market_intelligence.anti_hype import get_anti_hype
from core.market_intelligence.brief import generate_brief
from core.market_intelligence.memory import get_intel_memory
from core.market_intelligence.models import (
    Confidence,
    IntelligenceBrief,
    IntelligenceSource,
    MarketDomain,
    OpportunityAssessment,
    OpportunityScore,
    Sentiment,
    SignalType,
    SourceSignal,
    SourceTier,
)
from core.market_intelligence.opportunity_scorer import get_opportunity_scorer
from core.market_intelligence.signal_classifier import (
    classify_signal,
    classify_signal_type,
    detect_domain,
    detect_sentiment,
    extract_entities,
)
from core.market_intelligence.source_manager import get_source_manager, reset_source_manager

__all__ = [
    "SourceTier",
    "SignalType",
    "MarketDomain",
    "Sentiment",
    "Confidence",
    "IntelligenceSource",
    "SourceSignal",
    "OpportunityScore",
    "OpportunityAssessment",
    "IntelligenceBrief",
    "get_source_manager",
    "reset_source_manager",
    "classify_signal",
    "classify_signal_type",
    "detect_sentiment",
    "detect_domain",
    "extract_entities",
    "get_anti_hype",
    "get_opportunity_scorer",
    "generate_brief",
    "get_intel_memory",
]
