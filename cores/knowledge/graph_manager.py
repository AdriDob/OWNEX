from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class KnowledgeGraphNode:
    node_id: str
    node_type: str
    label: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class KnowledgeGraphEdge:
    edge_id: str
    source_id: str
    target_id: str
    relation_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class KnowledgeGraphManager(ABC):
    @abstractmethod
    def add_node(self, node: KnowledgeGraphNode) -> str: ...

    @abstractmethod
    def add_edge(self, edge: KnowledgeGraphEdge) -> str: ...

    @abstractmethod
    def get_node(self, node_id: str) -> KnowledgeGraphNode | None: ...

    @abstractmethod
    def get_neighbors(self, node_id: str) -> list[KnowledgeGraphEdge]: ...

    @abstractmethod
    def search_nodes(self, query: str, limit: int = 20) -> list[KnowledgeGraphNode]: ...


class InMemoryKnowledgeGraphManager(KnowledgeGraphManager):
    def __init__(self) -> None:
        self.nodes: dict[str, KnowledgeGraphNode] = {}
        self.edges: dict[str, KnowledgeGraphEdge] = {}
        self.adjacency: dict[str, list[str]] = {}

    def add_node(self, node: KnowledgeGraphNode) -> str:
        self.nodes[node.node_id] = node
        self.adjacency.setdefault(node.node_id, [])
        return node.node_id

    def add_edge(self, edge: KnowledgeGraphEdge) -> str:
        self.edges[edge.edge_id] = edge
        self.adjacency.setdefault(edge.source_id, []).append(edge.edge_id)
        self.adjacency.setdefault(edge.target_id, [])
        return edge.edge_id

    def get_node(self, node_id: str) -> KnowledgeGraphNode | None:
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> list[KnowledgeGraphEdge]:
        edge_ids = self.adjacency.get(node_id, [])
        return [self.edges[edge_id] for edge_id in edge_ids if edge_id in self.edges]

    def search_nodes(self, query: str, limit: int = 20) -> list[KnowledgeGraphNode]:
        results = []
        lower_query = query.lower()
        for node in self.nodes.values():
            if lower_query in node.label.lower() or lower_query in node.node_type.lower():
                results.append(node)
            if len(results) >= limit:
                break
        return results
