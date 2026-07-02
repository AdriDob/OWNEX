from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConfidenceScorerConfig:
    source_trust: dict[str, float] = field(default_factory=lambda: {
        "mitre": 1.0,
        "nvd": 0.95,
        "cve": 0.95,
        "owasp": 0.9,
        "portswigger": 0.9,
        "nuclei": 0.8,
        "payloadsallthethings": 0.75,
        "seclists": 0.75,
        "hackerone": 0.85,
        "bugcrowd": 0.85,
        "intigriti": 0.85,
        "yeswehack": 0.85,
        "public_report": 0.7,
        "technical_doc": 0.7,
        "orion_research": 0.95,
    })
    freshness_weight: float = 0.15
    source_weight: float = 0.35
    metadata_weight: float = 0.25
    entity_correlation_weight: float = 0.25
    max_confidence: float = 1.0
    min_confidence: float = 0.0


class ConfidenceScorer:
    def __init__(self, config: ConfidenceScorerConfig | None = None) -> None:
        self.config = config or ConfidenceScorerConfig()

    def compute(self, normalized_record: dict[str, Any]) -> float:
        metadata = normalized_record.get("metadata", {})
        source_type = metadata.get("source_type", "unknown").lower()
        base_trust = self.config.source_trust.get(source_type, 0.5)

        confidence = base_trust * self.config.source_weight
        confidence += self._freshness_score(metadata) * self.config.freshness_weight
        confidence += self._metadata_score(metadata) * self.config.metadata_weight
        confidence += self._entity_correlation_score(normalized_record) * self.config.entity_correlation_weight

        return max(self.config.min_confidence, min(self.config.max_confidence, confidence))

    def _freshness_score(self, metadata: dict[str, Any]) -> float:
        published_at = metadata.get("published_at")
        if not published_at:
            return 0.5
        return 0.9

    def _metadata_score(self, metadata: dict[str, Any]) -> float:
        score = 0.0
        if metadata.get("version"):
            score += 0.25
        if metadata.get("references"):
            score += 0.25
        if metadata.get("tags"):
            score += 0.25
        if metadata.get("technologies"):
            score += 0.25
        return min(1.0, score)

    def _entity_correlation_score(self, normalized_record: dict[str, Any]) -> float:
        entities = normalized_record.get("canonical_entities") or []
        return min(1.0, len(entities) / 5.0)
