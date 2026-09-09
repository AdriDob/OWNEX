"""Clasificador de señales — detecta, clasifica y extrae inteligencia de mensajes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from core.market_intelligence.models import (
    IntelligenceSource,
    MarketDomain,
    Sentiment,
    SignalType,
    SourceSignal,
)

logger = logging.getLogger("orion.intel.classifier")

# ── Keywords for signal classification ────────────────────────────────────

SIGNAL_PATTERNS: dict[str, list[str]] = {
    "scam_alert": [
        "scam",
        "rug",
        "hack",
        "breach",
        "exploit",
        "phishing",
        "malicious",
        "estafa",
        "timo",
        "fraude",
        "pump and dump",
        "honeypot",
    ],
    "opportunity": [
        "opportunity",
        "alpha",
        "gem",
        "undervalued",
        "hidden",
        "early",
        "before everyone",
        "insider",
        "breakout",
        "moon",
        "100x",
        "oportunidad",
        "ganga",
        "joya",
    ],
    "risk_warning": [
        "warning",
        "caution",
        "risk",
        "danger",
        "volatile",
        "correction",
        "dump",
        "crash",
        "bearish",
        "overheated",
        "bubble",
        "liquidate",
        "cuidado",
        "riesgo",
        "peligro",
        "corrección",
    ],
    "technical_setup": [
        "support",
        "resistance",
        "breakout",
        "breakdown",
        "volume spike",
        "rsi",
        "macd",
        "ema",
        "moving average",
        "trendline",
        "consolidation",
        "accumulation",
        "distribution",
        "wedge",
        "flag",
        "pattern",
    ],
    "fundamental": [
        "funding",
        "partnership",
        "integration",
        "mainnet",
        "testnet",
        "audit",
        " roadmap",
        "tokenomics",
        "vesting",
        "circulating supply",
        "total supply",
        "market cap",
        "tvl",
        "liquidity",
    ],
    "news_event": [
        "breaking",
        "announcement",
        "launch",
        "upgrade",
        "fork",
        "halving",
        "regulation",
        "sec",
        "etf",
        "approval",
        "ban",
        "legal",
        "noticia",
        "lanzamiento",
        "oficial",
    ],
    "promotion": [
        "shill",
        "promo",
        "giveaway",
        "airdrop",
        "free",
        "bonus",
        "referral",
        "affiliate",
        "paid",
        "sponsored",
        "ads",
    ],
}

SENTIMENT_KEYWORDS: dict[str, list[str]] = {
    "bullish": [
        "bullish",
        "moon",
        "pump",
        "rocket",
        "green",
        "growth",
        "strong",
        "buy",
        "long",
        "accumulate",
        "diamond",
        "hold",
        "hodl",
        "alcista",
        "sube",
        "compra",
        "al verde",
    ],
    "bearish": [
        "bearish",
        "dump",
        "red",
        "crash",
        "decline",
        "weak",
        "sell",
        "short",
        "drop",
        "falling",
        "correction",
        "capitulation",
        "bajista",
        "baja",
        "vende",
        "rojo",
        "desplome",
    ],
}

URGENCY_KEYWORDS: dict[str, list[str]] = {
    "critical": [
        "urgent",
        "emergency",
        "immediately",
        "critical",
        "asap",
        "now",
        "happening now",
        "breaking",
        "alert",
        "urgente",
        "emergencia",
        "inmediato",
        "ahora",
    ],
    "high": [
        "important",
        "warning",
        "attention",
        "significant",
        "major",
        "importante",
        "atención",
        "significativo",
    ],
}

DOMAIN_KEYWORDS: dict[MarketDomain, list[str]] = {
    MarketDomain.CRYPTO: [
        "bitcoin",
        "btc",
        "ethereum",
        "eth",
        "crypto",
        "altcoin",
        "coin",
        "token",
        "blockchain",
        "wallet",
        "exchange",
    ],
    MarketDomain.DEFI: [
        "defi",
        "lending",
        "borrowing",
        "staking",
        "yield",
        "liquidity pool",
        "dex",
        "amm",
        "swap",
        "farm",
        "vault",
        "protocol",
    ],
    MarketDomain.MEMECOIN: [
        "meme",
        "shitcoin",
        "pepe",
        "doge",
        "shib",
        "woof",
        "memecoin",
        "meme coin",
    ],
    MarketDomain.AI_CRYPTO: [
        "ai",
        "artificial intelligence",
        "gpt",
        "neural",
        "machine learning",
        "llm",
        "agent",
        "autonomous",
    ],
    MarketDomain.GAMING: [
        "gaming",
        "gamefi",
        "metaverse",
        "play to earn",
        "p2e",
        "nft game",
        "web3 game",
    ],
    MarketDomain.INFRASTRUCTURE: [
        "layer",
        "l1",
        "l2",
        "scaling",
        "bridge",
        "oracle",
        "interop",
        "rollup",
        "sidechain",
        "zk",
        "zero knowledge",
    ],
}


def classify_signal_type(text: str) -> SignalType:
    """Determine signal type from text content."""
    text_lower = text.lower()

    # Check for scam alerts first (highest priority)
    if any(kw in text_lower for kw in SIGNAL_PATTERNS["scam_alert"]):
        return SignalType.SCAM_ALERT

    # Check for risk warnings
    if any(kw in text_lower for kw in SIGNAL_PATTERNS["risk_warning"]):
        return SignalType.RISK_WARNING

    # Check for opportunities
    if any(kw in text_lower for kw in SIGNAL_PATTERNS["opportunity"]):
        return SignalType.OPPORTUNITY

    # Technical setups
    if any(kw in text_lower for kw in SIGNAL_PATTERNS["technical_setup"]):
        return SignalType.TECHNICAL_SETUP

    # Fundamentals
    if any(kw in text_lower for kw in SIGNAL_PATTERNS["fundamental"]):
        return SignalType.FUNDAMENTAL

    # News events
    if any(kw in text_lower for kw in SIGNAL_PATTERNS["news_event"]):
        return SignalType.NEWS_EVENT

    # Promotions
    if any(kw in text_lower for kw in SIGNAL_PATTERNS["promotion"]):
        return SignalType.PROMOTION

    # General sentiment keywords → market sentiment
    for _sent_type, words in SENTIMENT_KEYWORDS.items():
        if any(kw in text_lower for kw in words):
            return SignalType.MARKET_SENTIMENT

    return SignalType.GENERAL_DISCUSSION


def detect_sentiment(text: str) -> Sentiment:
    """Detect market sentiment from text."""
    text_lower = text.lower()
    bullish = sum(1 for kw in SENTIMENT_KEYWORDS["bullish"] if kw in text_lower)
    bearish = sum(1 for kw in SENTIMENT_KEYWORDS["bearish"] if kw in text_lower)

    if bullish > bearish and bullish >= 2:
        return Sentiment.BULLISH
    if bearish > bullish and bearish >= 2:
        return Sentiment.BEARISH
    if bullish > 0 and bearish > 0:
        return Sentiment.MIXED
    if bullish > 0 or bearish > 0:
        return Sentiment.BULLISH if bullish > bearish else Sentiment.BEARISH if bearish > bullish else Sentiment.NEUTRAL
    return Sentiment.NEUTRAL


def detect_urgency(text: str) -> str:
    """Detect urgency level."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in URGENCY_KEYWORDS["critical"]):
        return "critical"
    if any(kw in text_lower for kw in URGENCY_KEYWORDS["high"]):
        return "high"
    return "normal"


def detect_domain(text: str) -> MarketDomain:
    """Detect market domain from text."""
    text_lower = text.lower()
    scores: dict[MarketDomain, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[domain] = score
    if scores:
        return max(scores, key=scores.get)
    return MarketDomain.CRYPTO


def extract_entities(text: str) -> list[str]:
    """Extract mentioned entities (projects, tokens, protocols)."""
    entities = []
    # Common token/price patterns: $TOKEN, $100, etc
    import re

    dollar_tokens = re.findall(r"\$([A-Za-z0-9_]{2,20})", text)
    entities.extend(t.lower() for t in dollar_tokens)
    # Potential CVE mentions
    cves = re.findall(r"CVE-\d{4}-\d{4,}", text, re.IGNORECASE)
    entities.extend(cve.upper() for cve in cves)
    return list(set(entities))


def classify_signal(
    text: str,
    source: IntelligenceSource,
    title: str = "",
) -> SourceSignal:
    """Full signal classification pipeline."""
    signal_type = classify_signal_type(text)
    sentiment = detect_sentiment(text)
    urgency = detect_urgency(text)
    domain = detect_domain(text)
    entities = extract_entities(text)

    signal = SourceSignal(
        id=str(uuid4()),
        source_id=source.id,
        source_name=source.name,
        signal_type=signal_type,
        domain=domain,
        title=title or text[:80],
        body=text[:500],
        raw_text=text,
        sentiment=sentiment,
        urgency=urgency,
        entities=entities,
        source_tier=source.tier,
        posted_at=datetime.now(UTC).isoformat(),
    )

    logger.debug(
        "[INTEL] Signal classified: type=%s, domain=%s, sentiment=%s, urgency=%s, entities=%s",
        signal_type.value,
        domain.value,
        sentiment.value,
        urgency,
        entities,
    )
    return signal
