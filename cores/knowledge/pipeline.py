from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cores.knowledge.abstracts import (
    KnowledgeDeduplicator,
    KnowledgeEnricher,
    KnowledgeIndexer,
    KnowledgeNormalizer,
    KnowledgeParser,
    KnowledgePipeline,
    KnowledgePipelineReport,
    KnowledgePipelineStage,
    KnowledgeStore,
)
from cores.knowledge.trust import ConfidenceScorer


@dataclass
class KnowledgePipelineConfig:
    parser: KnowledgeParser
    normalizer: KnowledgeNormalizer
    deduplicator: KnowledgeDeduplicator
    enricher: KnowledgeEnricher
    indexer: KnowledgeIndexer
    store: KnowledgeStore
    confidence_scoring: ConfidenceScorer
    max_batch_size: int = 50


class KnowledgeIngestPipeline(KnowledgePipeline):
    def __init__(self, config: KnowledgePipelineConfig) -> None:
        self.config = config

    def run(self, payloads: list[dict[str, Any]]) -> list[str]:  # type: ignore[override]
        report = KnowledgePipelineReport()
        artifact_ids: list[str] = []

        if report.stages is None:
            report.stages = []

        for idx, payload in enumerate(payloads, start=1):
            stage = KnowledgePipelineStage(name=f"artifact_{idx}")
            stage.timestamp = datetime.utcnow().isoformat()
            if report.stages is not None:
                report.stages.append(stage)
            try:
                raw_doc = self.config.parser.parse(payload)
                normalized = self.config.normalizer.normalize(raw_doc)
                fingerprint = self.config.deduplicator.fingerprint(normalized)
                normalized["fingerprint"] = fingerprint
                existing = self.config.store.find_artifacts(fingerprint)

                if existing:
                    merged = self.config.deduplicator.merge(existing[0], normalized)
                    merged["metadata"]["confidence"] = self.config.confidence_scoring.compute(merged)
                    artifact_id = self.config.store.save_artifact(merged)
                else:
                    normalized["metadata"]["confidence"] = self.config.confidence_scoring.compute(normalized)
                    artifact_id = self.config.store.save_artifact(normalized)

                enriched = self.config.enricher.enrich(normalized)
                enriched["metadata"]["confidence"] = self.config.confidence_scoring.compute(enriched)
                self.config.indexer.index(enriched)
                artifact_id = self.config.store.save_artifact(enriched)
                artifact_ids.append(artifact_id)
                stage.complete(0.0, {"artifact_id": artifact_id})
            except Exception as exc:
                stage.status = "failed"
                stage.details = {"error": str(exc)}
                if report.errors is not None:
                    report.errors.append(str(exc))
                continue

        report.artifact_ids = artifact_ids
        return artifact_ids
