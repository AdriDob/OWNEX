from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from threading import Lock
from collections import defaultdict
import math


class NodeType(str, Enum):
    ROOT_DOMAIN = "root_domain"
    SUBDOMAIN = "subdomain"
    IP_ADDRESS = "ip_address"
    PORT = "port"
    SERVICE = "service"
    TECHNOLOGY = "technology"
    ENDPOINT = "endpoint"
    PARAMETER = "parameter"
    VULNERABILITY = "vulnerability"
    EXPLOIT = "exploit"
    CREDENTIAL = "credential"
    SESSION = "session"
    NOTE = "note"


class EdgeType(str, Enum):
    RESOLVES_TO = "resolves_to"
    HOSTS = "hosts"
    RUNS_ON = "runs_on"
    EXPOSES = "exposes"
    USES_TECH = "uses_tech"
    HAS_ENDPOINT = "has_endpoint"
    HAS_PARAMETER = "has_parameter"
    VULNERABLE_TO = "vulnerable_to"
    EXPLOITED_BY = "exploited_by"
    LEADS_TO = "leads_to"
    RELATED_TO = "related_to"
    AUTHENTICATES = "authenticates"


@dataclass(slots=True)
class GraphNode:
    id: str
    type: NodeType
    value: str
    label: str
    confidence: float = 1.0
    exploitability: float = 0.0
    risk_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    discovered_by: str | None = None
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: set[str] = field(default_factory=set)

    def merge(self, other: "GraphNode") -> None:
        self.confidence = max(self.confidence, other.confidence)
        self.exploitability = max(self.exploitability, other.exploitability)
        self.risk_score = max(self.risk_score, other.risk_score)
        self.metadata.update(other.metadata)
        self.tags.update(other.tags)
        self.updated_at = datetime.utcnow()


@dataclass(slots=True)
class GraphEdge:
    id: str
    source: str
    target: str
    type: EdgeType
    weight: float = 1.0
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    discovered_by: str | None = None
    discovered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class AttackPath:
    id: str
    nodes: list[str]
    edges: list[str]
    total_risk: float
    exploitability: float
    steps: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class AttackSurfaceGraph:
    def __init__(self):
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._reverse_adjacency: dict[str, set[str]] = defaultdict(set)
        self._type_index: dict[str, set[str]] = defaultdict(set)
        self._value_index: dict[str, str] = {}
        self._paths: dict[str, AttackPath] = {}
        self._lock = Lock()
        self._version = 0

    def add_node(
        self,
        node_type: NodeType,
        value: str,
        label: str | None = None,
        discovered_by: str | None = None,
        confidence: float = 1.0,
        exploitability: float = 0.0,
        risk_score: float = 0.0,
        metadata: dict[str, Any] | None = None,
        tags: set[str] | None = None,
    ) -> str:
        key = f"{node_type.value}:{value}"
        with self._lock:
            if key in self._value_index:
                node_id = self._value_index[key]
                node = self._nodes[node_id]
                node.confidence = max(node.confidence, confidence)
                node.exploitability = max(node.exploitability, exploitability)
                node.risk_score = max(node.risk_score, risk_score)
                if metadata:
                    node.metadata.update(metadata)
                if tags:
                    node.tags.update(tags)
                node.updated_at = datetime.utcnow()
                return node_id

            node_id = f"node_{uuid.uuid4().hex[:12]}"
            node = GraphNode(
                id=node_id,
                type=node_type,
                value=value,
                label=label or value,
                confidence=confidence,
                exploitability=exploitability,
                risk_score=risk_score,
                metadata=metadata or {},
                discovered_by=discovered_by,
                tags=tags or set(),
            )
            self._nodes[node_id] = node
            self._value_index[key] = node_id
            self._type_index[node_type.value].add(node_id)
            self._version += 1
            return node_id

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        weight: float = 1.0,
        confidence: float = 1.0,
        discovered_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        with self._lock:
            if source_id not in self._nodes or target_id not in self._nodes:
                return None
            edge_key = f"{source_id}:{edge_type.value}:{target_id}"
            edge_id = f"edge_{uuid.uuid4().hex[:12]}"
            edge = GraphEdge(
                id=edge_id,
                source=source_id,
                target=target_id,
                type=edge_type,
                weight=weight,
                confidence=confidence,
                metadata=metadata or {},
                discovered_by=discovered_by,
            )
            self._edges[edge_id] = edge
            self._adjacency[source_id].add(target_id)
            self._reverse_adjacency[target_id].add(source_id)
            self._version += 1
            return edge_id

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> GraphEdge | None:
        return self._edges.get(edge_id)

    def get_neighbors(self, node_id: str, edge_type: EdgeType | None = None) -> list[tuple[str, GraphEdge]]:
        result = []
        for target_id in self._adjacency.get(node_id, set()):
            for edge in self._edges.values():
                if edge.source == node_id and edge.target == target_id:
                    if edge_type is None or edge.type == edge_type:
                        result.append((target_id, edge))
        return result

    def get_predecessors(self, node_id: str, edge_type: EdgeType | None = None) -> list[tuple[str, GraphEdge]]:
        result = []
        for source_id in self._reverse_adjacency.get(node_id, set()):
            for edge in self._edges.values():
                if edge.source == source_id and edge.target == node_id:
                    if edge_type is None or edge.type == edge_type:
                        result.append((source_id, edge))
        return result

    def get_nodes_by_type(self, node_type: NodeType) -> list[GraphNode]:
        return [self._nodes[nid] for nid in self._type_index.get(node_type.value, set())]

    def find_attack_paths(
        self,
        start_types: list[NodeType] | None = None,
        target_types: list[NodeType] | None = None,
        max_depth: int = 5,
        min_risk: float = 0.0,
    ) -> list[AttackPath]:
        start_nodes = []
        if start_types:
            for t in start_types:
                start_nodes.extend(self.get_nodes_by_type(t))
        else:
            start_nodes = list(self._nodes.values())

        target_type_set = set(t.value for t in target_types) if target_types else None

        paths = []
        for start in start_nodes:
            paths.extend(self._dfs_paths(start.id, set(), [], [], 0, max_depth, target_type_set, min_risk))

        paths.sort(key=lambda p: p.total_risk, reverse=True)
        return paths[:50]

    def _dfs_paths(
        self,
        current: str,
        visited: set[str],
        nodes: list[str],
        edges: list[str],
        depth: int,
        max_depth: int,
        target_types: set[str] | None,
        min_risk: float,
    ) -> list[AttackPath]:
        if depth >= max_depth or current in visited:
            return []

        visited.add(current)
        nodes.append(current)
        node = self._nodes.get(current)
        if not node:
            return []

        paths = []
        is_target = target_types is None or node.type.value in target_types

        if is_target and node.risk_score >= min_risk and len(nodes) > 1:
            total_risk = sum(self._nodes[n].risk_score for n in nodes)
            exploitability = max(self._nodes[n].exploitability for n in nodes)
            path_id = f"path_{uuid.uuid4().hex[:12]}"
            steps = []
            for i, (n, e) in enumerate(zip(nodes, edges)):
                edge = self._edges.get(e)
                steps.append({"node": n, "edge": edge.type.value if edge else None, "risk": self._nodes[n].risk_score})
            paths.append(
                AttackPath(
                    id=path_id,
                    nodes=nodes.copy(),
                    edges=edges.copy(),
                    total_risk=total_risk,
                    exploitability=exploitability,
                    steps=steps,
                )
            )

        for target_id, edge in self.get_neighbors(current):
            if target_id in visited:
                continue
            paths.extend(
                self._dfs_paths(
                    target_id, visited, nodes, edges + [edge.id], depth + 1, max_depth, target_types, min_risk
                )
            )

        visited.remove(current)
        nodes.pop()
        return paths

    def calculate_node_risk(self, node_id: str) -> float:
        node = self._nodes.get(node_id)
        if not node:
            return 0.0
        base = node.risk_score
        for target_id, edge in self.get_neighbors(node_id):
            target = self._nodes.get(target_id)
            if target and target.type == NodeType.VULNERABILITY:
                base += target.risk_score * edge.weight * 0.5
        return min(10.0, base)

    def update_exploitability(self, node_id: str, delta: float) -> None:
        node = self._nodes.get(node_id)
        if node:
            node.exploitability = max(0.0, min(1.0, node.exploitability + delta))
            node.updated_at = datetime.utcnow()

    def export_json(self) -> str:
        data = {
            "version": self._version,
            "nodes": {
                nid: {
                    "id": n.id,
                    "type": n.type.value,
                    "value": n.value,
                    "label": n.label,
                    "confidence": n.confidence,
                    "exploitability": n.exploitability,
                    "risk_score": n.risk_score,
                    "metadata": n.metadata,
                    "discovered_by": n.discovered_by,
                    "discovered_at": n.discovered_at.isoformat(),
                    "tags": list(n.tags),
                }
                for nid, n in self._nodes.items()
            },
            "edges": {
                eid: {
                    "id": e.id,
                    "source": e.source,
                    "target": e.target,
                    "type": e.type.value,
                    "weight": e.weight,
                    "confidence": e.confidence,
                    "metadata": e.metadata,
                    "discovered_by": e.discovered_by,
                    "discovered_at": e.discovered_at.isoformat(),
                }
                for eid, e in self._edges.items()
            },
        }
        return json.dumps(data, indent=2)

    def get_stats(self) -> dict[str, Any]:
        type_counts = defaultdict(int)
        for n in self._nodes.values():
            type_counts[n.type.value] += 1
        return {
            "version": self._version,
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "node_types": dict(type_counts),
        }


graph = AttackSurfaceGraph()
