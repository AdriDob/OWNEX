"""API de Inteligencia de Mercado ORION."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from core.market_intelligence import (
    IntelligenceSource,
    MarketDomain,
    SourceTier,
    generate_brief,
    get_anti_hype,
    get_intel_memory,
    get_opportunity_scorer,
    get_source_manager,
)
from core.market_intelligence.signal_classifier import (
    classify_signal,
    classify_signal_type,
    detect_domain,
    detect_sentiment,
)

logger = logging.getLogger("orion.intel.api")
router = APIRouter(prefix="/api/intel", tags=["market_intelligence"])

sm = get_source_manager()
ah = get_anti_hype()
scorer = get_opportunity_scorer()
memory = get_intel_memory()


# ── Sources ──


@router.post("/sources/register")
def register_source(data: dict[str, Any]):
    """Register an intelligence source."""
    tier = SourceTier(data.get("tier", "b"))
    domain = MarketDomain(data.get("domain", "crypto"))
    source = sm.register_telegram(
        channel_id=data["channel_id"],
        name=data["name"],
        tier=tier,
        domain=domain,
        tags=data.get("tags", []),
        url=data.get("url", ""),
        description=data.get("description", ""),
    )
    return {"success": True, "source": source.__dict__}


@router.get("/sources")
def list_sources(tier: str | None = None, domain: str | None = None):
    """List registered intelligence sources."""
    tier_filter = SourceTier(tier) if tier else None
    domain_filter = MarketDomain(domain) if domain else None
    sources = sm.list(tier=tier_filter, domain=domain_filter)
    return {
        "success": True,
        "sources": [s.__dict__ for s in sources],
        "total": len(sources),
    }


@router.get("/sources/{source_id}")
def get_source(source_id: str):
    """Get a single source with stats."""
    source = sm.get(source_id)
    if not source:
        return {"success": False, "error": "source not found"}
    return {
        "success": True,
        "source": source.__dict__,
        "correct": sm.get_correct_count(source_id),
        "total": sm.get_total_count(source_id),
        "accuracy": source.accuracy,
    }


@router.delete("/sources/{source_id}")
def delete_source(source_id: str):
    """Remove an intelligence source."""
    ok = sm.unregister(source_id)
    return {"success": ok}


@router.post("/sources/{source_id}/outcome")
def record_source_outcome(source_id: str, data: dict[str, Any]):
    """Record whether a signal from this source was correct."""
    correct = data.get("correct", False)
    details = data.get("details", "")
    sm.record_outcome(source_id, correct=correct, details=details)
    if memory:
        memory.record_outcome(
            signal_id=data.get("signal_id", "unknown"),
            source_id=source_id,
            correct=correct,
            details=details,
            value_usd=data.get("value_usd", 0.0),
        )
    source = sm.get(source_id)
    return {"success": True, "accuracy": source.accuracy if source else 0.0}


# ── Signal classification ──


@router.post("/classify")
def classify_message(data: dict[str, Any]):
    """Classify a raw message as a signal."""
    text = data.get("text", "")
    title = data.get("title", "")
    source_id = data.get("source_id", "manual")

    # If source exists, use it; otherwise create a temporary one
    source = sm.get(source_id)
    if not source:
        source = IntelligenceSource(
            id=source_id,
            name=data.get("source_name", "Manual"),
            source_type="manual",
            tier=SourceTier.B,
            domain=MarketDomain.CRYPTO,
        )

    signal = classify_signal(text, source, title=title)

    # Anti-hype analysis
    flags = ah.analyze(signal)
    signal.manipulation_flags = flags

    # Confidence assessment
    signal.confidence = ah.get_confidence(signal)

    return {
        "success": True,
        "signal": {
            "id": signal.id,
            "signal_type": signal.signal_type.value,
            "domain": signal.domain.value,
            "sentiment": signal.sentiment.value,
            "urgency": signal.urgency,
            "confidence": signal.confidence.value,
            "entities": signal.entities,
            "manipulation_flags": signal.manipulation_flags,
        },
    }


@router.post("/classify/text")
def classify_text_direct(data: dict[str, Any]):
    """Quick text classification (signal type + sentiment + domain)."""
    text = data.get("text", "")
    return {
        "success": True,
        "signal_type": classify_signal_type(text).value,
        "sentiment": detect_sentiment(text).value,
        "domain": detect_domain(text).value,
        "manipulation_flags": ah.analyze_text(text),
    }


# ── Opportunity scoring ──


@router.post("/score")
def score_opportunity(data: dict[str, Any]):
    """Score a classified signal as an opportunity."""
    text = data.get("text", "")
    source_id = data.get("source_id", "manual")

    source = sm.get(source_id)
    if not source:
        source = IntelligenceSource(
            id=source_id,
            name=data.get("source_name", "Manual"),
            source_type="manual",
            tier=SourceTier.B,
            domain=MarketDomain.CRYPTO,
        )

    signal = classify_signal(text, source, title=data.get("title", ""))
    ah.analyze(signal)
    signal.confidence = ah.get_confidence(signal)

    assessment = scorer.score_signal(signal)

    return {
        "success": True,
        "opportunity": {
            "id": assessment.id,
            "title": assessment.title,
            "score": assessment.score.to_dict(),
            "confidence": assessment.confidence.value,
            "strengths": assessment.strengths,
            "risks": assessment.risks,
            "recommended_action": assessment.recommended_action,
        },
    }


# ── Briefing ──


@router.post("/brief/generate")
def generate_intel_brief(data: dict[str, Any] | None = None):
    """Generate intelligence briefing from current state."""
    level = (data or {}).get("level", "summary")
    opportunities = []  # TODO: load from stored signals/scored opportunities
    signals = []
    sources = sm.list()

    brief = generate_brief(
        opportunities=opportunities,
        signals=signals,
        sources=sources,
    )

    return {
        "success": True,
        "brief": {
            "date": brief.date,
            "summary": brief.summary,
            "signals_analyzed": brief.signals_analyzed,
            "sources_active": brief.sources_active,
            "trends": brief.trends,
            "learned": brief.learned,
            "top_actions": brief.top_actions,
        },
        "markdown": brief.to_markdown(level=level),
    }


# ── Anti-hype ──


@router.post("/analyze/manipulation")
def analyze_manipulation(data: dict[str, Any]):
    """Check text for manipulation patterns."""
    text = data.get("text", "")
    flags = ah.analyze_text(text)
    return {
        "success": True,
        "flags": flags,
        "flag_count": len(flags),
        "is_clean": len(flags) == 0,
    }


# ── Memory ──


@router.get("/memory/stats")
def memory_stats():
    """Get intelligence memory statistics."""
    return {"success": True, "stats": memory.stats() if memory else {}}


@router.get("/memory/predictions/pending")
def pending_predictions():
    """List pending unverified predictions."""
    if not memory:
        return {"success": False, "error": "memory not available"}
    return {"success": True, "predictions": memory.pending_predictions()}


@router.post("/memory/predictions/verify")
def verify_prediction(data: dict[str, Any]):
    """Verify a prediction as correct/incorrect."""
    pred_id = data.get("prediction_id", "")
    correct = data.get("correct", False)
    if not memory:
        return {"success": False, "error": "memory not available"}
    ok = memory.verify_prediction(pred_id, correct=correct)
    return {"success": ok}


# ── Stats ──


@router.get("/stats")
def intel_stats():
    """Overall intelligence module stats."""
    return {
        "success": True,
        "sources": sm.stats(),
        "memory": memory.stats() if memory else {},
    }
