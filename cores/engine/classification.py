"""Classification Engine — decides if an observation is an opportunity.

Three-layer classification:
  Layer 1 (RULES):  fast, covers 90% of cases
  Layer 2 (HEURISTICS): medium, covers 9%
  Layer 3 (LLM):    expensive, only for ambiguous cases (1%)
"""

from __future__ import annotations

import contextlib
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.engine.base import Engine
from core.sensors.observation import Observation

logger = logging.getLogger("ownex.classification")


@dataclass
class ClassificationResult:
    """Result of classifying an observation."""

    is_opportunity: bool
    opportunity_id: str | None = None
    cycle: str | None = None  # "security", "forge", "pulse", "vault", "atlas"
    source_type: str | None = None  # "bug_bounty", "dev_bounty", "ai_work", etc.
    tags: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""
    layer: str = "rules"  # "rules", "heuristics", "llm"


@dataclass
class Opportunity:
    """An opportunity — an observation that passed classification.

    This is the output of ClassificationEngine and the input to
    StrategyEngine (and eventually PipelineEngine).
    """

    id: str
    name: str
    description: str
    url: str | None

    # Classification
    cycle: str  # "security", "forge", "pulse", "vault", "atlas"
    source_type: str  # "bug_bounty", "dev_bounty", "ai_work", etc.
    source_name: str  # sensor_id or platform name
    tags: list[str]

    # Economics
    estimated_reward_min: float = 0.0
    estimated_reward_max: float = 0.0
    estimated_effort_hours: float = 0.0

    # Quality
    confidence: float = 0.5
    layer: str = "rules"  # classification layer used

    # Raw
    raw_data: dict[str, Any] = field(default_factory=dict)

    # Timing
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    # Pipeline status
    status: str = "new"  # new | planned | prepared | executed | validated | archived


# ── Classifier interface ───────────────────────────────────────────


class Classifier(ABC):
    """A classifier decides if an observation is an opportunity."""

    @abstractmethod
    async def classify(self, observation: Observation) -> ClassificationResult: ...


# ── Rule-based classifiers (Layer 1) ───────────────────────────────


SOURCE_TYPE_MAP: dict[str, str] = {
    "bug_bounty": "security",
    "dev_bounty": "forge",
    "ai_work": "pulse",
    "microtask": "pulse",
    "freelance": "forge",
    "oss_sponsor": "forge",
    "job_application": "pulse",
    "investment": "vault",
    "intel": "atlas",
}


class SourceTypeClassifier(Classifier):
    """Classifies based on the sensor's source_type.

    Fastest path: the sensor already knows what it observed.
    """

    async def classify(self, observation: Observation) -> ClassificationResult:
        source_type = observation.source_type
        cycle = SOURCE_TYPE_MAP.get(source_type)

        if cycle:
            return ClassificationResult(
                is_opportunity=True,
                cycle=cycle,
                source_type=source_type,
                confidence=0.9,
                reason=f"Source type {source_type} → cycle {cycle}",
                layer="rules",
            )
        return ClassificationResult(
            is_opportunity=False,
            reason=f"Unknown source type: {source_type}",
            layer="rules",
        )


class RewardClassifier(Classifier):
    """Classifies based on reward presence and magnitude."""

    MIN_REWARD_THRESHOLD = 5.0

    async def classify(self, observation: Observation) -> ClassificationResult:
        if observation.estimated_reward_max < self.MIN_REWARD_THRESHOLD:
            return ClassificationResult(
                is_opportunity=False,
                reason=f"Reward ${observation.estimated_reward_max:.2f} below ${self.MIN_REWARD_THRESHOLD:.2f}",
                layer="rules",
            )

        return ClassificationResult(
            is_opportunity=True,
            confidence=0.6,
            reason="Has reward above threshold",
            layer="rules",
        )


TEXT_PATTERNS: dict[str, list[str]] = {
    "security": [
        r"\b(bug\s*bounty|bbp|vdp)\b",
        r"\b(xss|csrf|ssrf|sqli|rce|lfi|idor)\b",
        r"\b(vulnerability|exploit|cve|pentest)\b",
        r"\b(hackerone|bugcrowd|intigriti|immunefi|yeswehack)\b",
    ],
    "forge": [
        r"\b(bounty|bounties)\b",
        r"\b(issue\s*hunt|algora|opire|superteam)\b",
        r"\b(gitcoin|bountysource)\b",
        r"\b(sponsor|funding|grant)\b",
    ],
    "pulse": [
        r"\b(ai\s*train|data\s*label|data\s*annot)\b",
        r"\b(microtask|micro.task)\b",
        r"\b(outlier|mindrift|remotask)\b",
        r"\b(hourly\s*rate|per\s*hour)\b",
    ],
    "vault": [
        r"\b(invest|trading|defi|yield)\b",
        r"\b(audit|smart\s*contract)\b",
    ],
}


class PatternClassifier(Classifier):
    """Classifies by regex patterns in title/description/tags."""

    PATTERNS = TEXT_PATTERNS

    async def classify(self, observation: Observation) -> ClassificationResult:
        text = f"{observation.title} {observation.description} {' '.join(observation.tags)}".lower()

        scores: dict[str, int] = {}
        for cycle, patterns in self.PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text)
                score += len(matches)
            if score > 0:
                scores[cycle] = score

        if not scores:
            return ClassificationResult(
                is_opportunity=False,
                reason="No pattern matched title/description/tags",
                layer="rules",
            )

        best_cycle = max(scores, key=lambda k: scores[k])
        return ClassificationResult(
            is_opportunity=True,
            cycle=best_cycle,
            source_type="unknown",
            tags=observation.tags,
            confidence=min(0.5 + scores[best_cycle] * 0.1, 0.95),
            reason=f"Pattern match: {best_cycle} ({scores[best_cycle]} hits)",
            layer="rules",
        )


# ── Composite classifier ──────────────────────────────────────────


class CompositeClassifier(Classifier):
    """Runs classifiers in order, stops when confident enough.

    Fast path: rules (Layer 1, <1ms, 90% of cases)
    Medium path: heuristics (Layer 2, <100ms, 9% of cases)
    Slow path: LLM (Layer 3, >1s, 1% of cases)
    """

    def __init__(self) -> None:
        self.rules: list[Classifier] = [
            SourceTypeClassifier(),
            RewardClassifier(),
            PatternClassifier(),
        ]
        self.heuristics: list[Classifier] = []
        self.llm: Classifier | None = None

    async def classify(self, observation: Observation) -> ClassificationResult:
        best_positive: ClassificationResult | None = None

        # Layer 1: Rules — fast path returns immediately when confident
        for classifier in self.rules:
            result = await classifier.classify(observation)
            if result.is_opportunity and result.confidence >= 0.8:
                return result
            if not result.is_opportunity and result.confidence >= 0.9:
                return result
            if result.is_opportunity and (best_positive is None or result.confidence >= best_positive.confidence):
                best_positive = result

        # Return best positive from rules if any
        if best_positive:
            return best_positive

        # Layer 2: Heuristics
        for classifier in self.heuristics:
            result = await classifier.classify(observation)
            if result.is_opportunity and result.confidence >= 0.7:
                return result

        # Layer 3: LLM
        if self.llm:
            return await self.llm.classify(observation)

        # Fallback: noise
        return ClassificationResult(
            is_opportunity=False,
            reason="All classifiers failed to reach confidence threshold",
            layer="rules",
        )


# ── Classification Engine ──────────────────────────────────────────


class ClassificationEngine(Engine):
    """Orchestrates classification of observations.

    Observation → ClassificationResult → Opportunity | discarded
    """

    name = "classification_engine"

    def __init__(self, event_bus: Any | None = None) -> None:
        super().__init__()
        self.classifier = CompositeClassifier()
        self.event_bus = event_bus

    async def initialize(self) -> None:
        self._initialized = True

    async def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "name": self.name,
        }

    async def classify(self, observation: Observation) -> Opportunity | None:
        """Classify a single observation.

        Returns Opportunity if it's actionable, None if noise.
        """
        result = await self.classifier.classify(observation)

        if not result.is_opportunity:
            self._emit(
                "observation:discarded",
                {
                    "observation_id": observation.id,
                    "reason": result.reason,
                    "layer": result.layer,
                },
            )
            return None

        opportunity = Opportunity(
            id=observation.id,
            name=observation.title,
            description=observation.description,
            url=observation.url,
            cycle=result.cycle or "atlas",
            source_type=result.source_type or "unknown",
            source_name=observation.sensor_id,
            tags=result.tags or observation.tags,
            estimated_reward_min=observation.estimated_reward_min,
            estimated_reward_max=observation.estimated_reward_max,
            estimated_effort_hours=observation.estimated_effort_hours,
            confidence=result.confidence,
            layer=result.layer,
            raw_data=observation.raw_data,
        )

        self._emit(
            "opportunity:created",
            {
                "opportunity_id": opportunity.id,
                "cycle": opportunity.cycle,
                "source_type": opportunity.source_type,
            },
        )

        return opportunity

    async def classify_all(self, observations: list[Observation]) -> list[Opportunity]:
        """Classify a batch of observations, return only opportunities."""
        opportunities: list[Opportunity] = []
        for obs in observations:
            opp = await self.classify(obs)
            if opp:
                opportunities.append(opp)
        return opportunities

    def _emit(self, event: str, data: dict[str, Any]) -> None:
        if self.event_bus:
            with contextlib.suppress(Exception):
                self.event_bus.publish(event, **data)
