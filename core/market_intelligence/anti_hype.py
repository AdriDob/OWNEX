"""Anti-Hype Engine — detecta manipulación, FOMO, ruido y baja calidad."""

from __future__ import annotations

import logging
import re
from typing import Any

from core.market_intelligence.models import Confidence, SourceSignal, SourceTier

logger = logging.getLogger("orion.intel.anti_hype")

# ── Manipulation patterns ─────────────────────────────────────────────────

MANIPULATION_PATTERNS: list[dict[str, Any]] = [
    {
        "name": "guaranteed_returns",
        "patterns": [
            r"guaranteed\s+(profit|return|x)",
            r"100%\s+(win|profit|safe|secure)",
            r"risk[-\s]free",
            r"ganancia\s+garantizada",
            r"seguro\s+100%",
        ],
    },
    {
        "name": "urgency_fomo",
        "patterns": [
            r"(last|final)\s+(call|chance|opportunity)",
            r"don'?t\s+(miss|lose)",
            r"act\s+(now|fast|quickly)",
            r"limited\s+(time|offer|supply)",
            r"última\s+(oportunidad|chance|vez)",
            r"no\s+(te\s+)?lo\s+pierdas",
        ],
    },
    {
        "name": "price_pumping",
        "patterns": [
            r"(to\s+the\s+)?moon",
            r"100x",
            r"1000x",
            r"x100",
            r"easy\s+money",
            r"get\s+rich",
            r"lambo",
            r"when\s+(lambo|moon)",
            r"al\s+infinito",
            r"a\s+la\s+luna",
            r"riqueza\s+fácil",
        ],
    },
    {
        "name": "fake_authority",
        "patterns": [
            r"(insider|whale|dev|team)\s+(said|says|reveals|confirmed)",
            r"(confirmed|leaked|secret)\s+(info|news|partnership)",
            r"confidencial",
            r"info\s+privilegiada",
            r"filtrado",
            r"insider",
            r"whale\s+accumulating",
        ],
    },
    {
        "name": "emotional_pressure",
        "patterns": [
            r"(don'?t\s+)?(regret|fomo|miss)",
            r"you'?ll\s+(thank|hate)\s+(me|yourself)",
            r"best\s+opportunity\s+(ever|of\s+your\s+life)",
            r"arrepentir",
            r"no\s+te\s+lo\s+pierdas",
        ],
    },
    {
        "name": "no_evidence",
        "patterns": [
            r"(trust\s+me|believe\s+me|just\s+trust)",
            r"do\s+your\s+own\s+research",
            r"nfa|not\s+financial\s+advice",
            r"dyor",
            r"solo\s+confía",
            r"haz\s+tu\s+propia\s+investigación",
        ],
    },
    {
        "name": "scam_crypto",
        "patterns": [
            r"send\s+\d+\s+(eth|btc|bnb|sol)",
            r"double\s+your\s+(btc|eth|crypto)",
            r"free\s+(money|eth|btc|crypto)",
            r"giveaway",
            r"envía\s+\d+",
            r"duplica\s+tus\s+",
        ],
    },
    {
        "name": "repetition_pump",
        "patterns": [
            r"(buy|pump|moon|gem|hodl)\s+(now|soon|fast)",
            r"compr(a|en)\s+(ahora|ya)",
            r"vamos\s+(que\s+)?sube",
        ],
    },
]


class AntiHypeEngine:
    """Detects manipulation, FOMO, and low-quality signals."""

    def __init__(self) -> None:
        self._compiled: list[dict[str, Any]] = []
        for rule in MANIPULATION_PATTERNS:
            compiled = {
                "name": rule["name"],
                "patterns": [re.compile(p, re.IGNORECASE) for p in rule["patterns"]],
            }
            self._compiled.append(compiled)

    def analyze(self, signal: SourceSignal) -> list[str]:
        """Analyze a signal for manipulation flags. Returns list of flag names."""
        flags: list[str] = []
        text = signal.body or signal.raw_text or signal.title

        for rule in self._compiled:
            for pattern in rule["patterns"]:
                if pattern.search(text):
                    flags.append(rule["name"])
                    break

        # Source tier-based adjustments
        if signal.source_tier == SourceTier.C:
            flags.append("low_tier_source")

        signal.manipulation_flags = flags

        if flags:
            logger.info(
                "[ANTIHYPE] Signal %s flagged: %s",
                signal.id[:8],
                ", ".join(flags),
            )

        return flags

    def get_confidence(self, signal: SourceSignal) -> Confidence:
        """Adjust confidence based on manipulation flags."""
        flags = signal.manipulation_flags or self.analyze(signal)
        flag_count = len(flags)

        if flag_count >= 4:
            return Confidence.VERY_LOW
        if flag_count >= 2:
            return Confidence.LOW
        if flag_count >= 1:
            return Confidence.MEDIUM

        # Source tier adjustment
        if signal.source_tier == SourceTier.A:
            return Confidence.HIGH
        if signal.source_tier == SourceTier.B:
            return Confidence.MEDIUM
        return Confidence.LOW

    def analyze_text(self, text: str, source_tier: SourceTier = SourceTier.B) -> list[str]:
        """Quick text analysis without a full signal object."""
        flags: list[str] = []
        for rule in self._compiled:
            for pattern in rule["patterns"]:
                if pattern.search(text):
                    flags.append(rule["name"])
                    break
        if source_tier == SourceTier.C:
            flags.append("low_tier_source")
        return flags


_ANTI_HYPE: AntiHypeEngine | None = None


def get_anti_hype() -> AntiHypeEngine:
    global _ANTI_HYPE
    if _ANTI_HYPE is None:
        _ANTI_HYPE = AntiHypeEngine()
    return _ANTI_HYPE
