from __future__ import annotations

import logging
from abc import ABC
from typing import Any

from cores.knowledge.abstracts import KnowledgeSourceConnector, KnowledgeStore
from cores.knowledge.graph import KnowledgeGraphManager, KnowledgeGraphNode, KnowledgeGraphEdge
from cores.knowledge.pipeline import KnowledgeIngestPipeline, KnowledgePipelineConfig
from cores.knowledge.trust import ConfidenceScorer

logger = logging.getLogger("rastro.knowledge.manager")


class KnowledgeManager(ABC):
    def __init__(
        self,
        store: KnowledgeStore,
        graph: KnowledgeGraphManager,
        pipeline: KnowledgeIngestPipeline,
        connectors: list[KnowledgeSourceConnector],
    ) -> None:
        self.store = store
        self.graph = graph
        self.pipeline = pipeline
        self.connectors = connectors

    def ingest_from_source(self, source_name: str) -> list[str]:
        connector = self._find_connector(source_name)
        if not connector:
            raise ValueError(f"Unknown knowledge source: {source_name}")

        raw_items = connector.discover()
        artifact_ids = self.pipeline.run(raw_items)
        logger.info("Ingested %d artifacts from %s", len(artifact_ids), source_name)
        return artifact_ids

    def _find_connector(self, source_name: str) -> KnowledgeSourceConnector | None:
        for connector in self.connectors:
            if connector.name == source_name:
                return connector
        return None

    def register_connector(self, connector: KnowledgeSourceConnector) -> None:
        self.connectors.append(connector)

    def register_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        confidence: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        edge = KnowledgeGraphEdge(
            edge_id=f"rel::{source_id}::{target_id}::{relation_type}",
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            metadata=metadata or {},
            confidence=confidence,
        )
        return self.graph.add_edge(edge)

    def add_entity_node(
        self,
        node_id: str,
        node_type: str,
        label: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        node = KnowledgeGraphNode(
            node_id=node_id,
            node_type=node_type,
            label=label,
            metadata=metadata or {},
        )
        return self.graph.add_node(node)

    def index_artifact(self, artifact_id: str, artifact: dict[str, Any]) -> None:
        self.pipeline.config.indexer.index(artifact)
        logger.info("Indexed artifact %s", artifact_id)
