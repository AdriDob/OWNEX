"""Knowledge Graph — unified graph connecting all ORION entities.

Relates targets, companies, findings, reports, rewards, invoices, events,
decisions, CVEs, technologies, wallets, exchanges, and everything else.

Usage:

    from cores.knowledge.graph import get_knowledge_graph

    kg = get_knowledge_graph()

    # Add nodes
    target = kg.add_node("target", "example.com", {"domain": "example.com"})
    finding = kg.add_node("finding", "IDOR in /api/users", {"severity": "high"})

    # Connect them
    kg.add_edge(target.id, finding.id, "has_finding")

    # Query
    neighbors = kg.get_neighbors(target.id)
    path = kg.get_path(target.id, finding.id)
"""

from __future__ import annotations

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.knowledge.graph")


# ── Enums ──────────────────────────────────────────────────────


class NodeTypes(StrEnum):
    TARGET = "target"
    COMPANY = "company"
    DOMAIN = "domain"
    SUBDOMAIN = "subdomain"
    ENDPOINT = "endpoint"
    FINDING = "finding"
    REPORT = "report"
    REWARD = "reward"
    INVOICE = "invoice"
    EVENT = "event"
    DECISION = "decision"
    CVE = "cve"
    TECHNOLOGY = "technology"
    WALLET = "wallet"
    EXCHANGE = "exchange"
    BROKER = "broker"
    MARKET = "market"
    USER = "user"
    WORKFLOW = "workflow"
    PLAYBOOK = "playbook"
    TOOL = "tool"
    SERVICE = "service"


class EdgeTypes(StrEnum):
    HAS_FINDING = "has_finding"
    HAS_REPORT = "has_report"
    HAS_REWARD = "has_reward"
    HAS_INVOICE = "has_invoice"
    HAS_DECISION = "has_decision"
    HAS_CVE = "has_cve"
    HAS_TECHNOLOGY = "has_technology"
    HAS_SUBDOMAIN = "has_subdomain"
    HAS_ENDPOINT = "has_endpoint"
    HAS_EVENT = "has_event"
    HAS_WALLET = "has_wallet"
    BELONGS_TO = "belongs_to"
    DETECTED_ON = "detected_on"
    GENERATED = "generated"
    PAYS = "pays"
    USES = "uses"
    RELATED_TO = "related_to"
    TRIGGERED = "triggered"
    PRODUCES = "produces"
    LEADS_TO = "leads_to"
    FEEDS_INTO = "feeds_into"


# ── Data classes ───────────────────────────────────────────────


@dataclass(slots=True)
class KnowledgeGraphNode:
    node_id: str
    node_type: str
    label: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(slots=True)
class KnowledgeGraphEdge:
    edge_id: str
    source_id: str
    target_id: str
    relation_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# ── In-memory implementation ───────────────────────────────────


class KnowledgeGraphManager:
    """In-memory knowledge graph manager."""

    def __init__(self) -> None:
        self.nodes: dict[str, KnowledgeGraphNode] = {}
        self.edges: dict[str, KnowledgeGraphEdge] = {}
        self._adj: dict[str, set[str]] = {}

    def add_node(self, node: KnowledgeGraphNode) -> str:
        self.nodes[node.node_id] = node
        if node.node_id not in self._adj:
            self._adj[node.node_id] = set()
        return node.node_id

    def get_node(self, node_id: str) -> KnowledgeGraphNode | None:
        return self.nodes.get(node_id)

    def find_nodes(
        self,
        node_type: str | None = None,
        name_pattern: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KnowledgeGraphNode]:
        results = []
        for node in self.nodes.values():
            if node_type and node.node_type != node_type:
                continue
            if name_pattern and name_pattern.lower() not in node.label.lower():
                continue
            results.append(node)
        results.sort(key=lambda n: n.updated_at, reverse=True)
        return results[offset : offset + limit]

    def add_edge(self, edge: KnowledgeGraphEdge) -> str:
        self.edges[edge.edge_id] = edge
        self._adj.setdefault(edge.source_id, set()).add(edge.target_id)
        self._adj.setdefault(edge.target_id, set()).add(edge.source_id)
        return edge.edge_id

    def get_edges(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        edge_type: str | None = None,
        limit: int = 100,
    ) -> list[KnowledgeGraphEdge]:
        results = []
        for edge in self.edges.values():
            if source_id and edge.source_id != source_id:
                continue
            if target_id and edge.target_id != target_id:
                continue
            if edge_type and edge.relation_type != edge_type:
                continue
            results.append(edge)
        results.sort(key=lambda e: e.created_at, reverse=True)
        return results[:limit]

    def get_neighbors(
        self, node_id: str, edge_type: str | None = None, direction: str = "both", max_depth: int = 1
    ) -> list[dict[str, Any]]:
        visited: set[str] = set()
        results: list[dict[str, Any]] = []
        queue: deque[tuple[str, int]] = deque()
        queue.append((node_id, 0))
        visited.add(node_id)

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            # Get edges for current node
            edges = []
            for edge in self.edges.values():
                if edge.relation_type == "edge_type" if edge_type else True:
                    pass
                if direction == "outgoing" and edge.source_id != current_id:
                    continue
                if direction == "incoming" and edge.target_id != current_id:
                    continue
                if direction == "both" and edge.source_id != current_id and edge.target_id != current_id:
                    continue
                edges.append(edge)

            for edge in edges:
                neighbor_id = edge.target_id if edge.source_id == current_id else edge.source_id
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    neighbor = self.nodes.get(neighbor_id)
                    if neighbor:
                        entry = {
                            "node": {
                                "id": neighbor.node_id,
                                "node_type": neighbor.node_type,
                                "label": neighbor.label,
                                "metadata": neighbor.metadata,
                            },
                            "edge": {
                                "id": edge.edge_id,
                                "type": edge.relation_type,
                                "weight": 1.0,
                                "direction": "outgoing" if edge.source_id == current_id else "incoming",
                            },
                            "depth": depth + 1,
                        }
                        results.append(entry)
                        queue.append((neighbor_id, depth + 1))

        return results


# ── KnowledgeGraph wrapper for backward compatibility ────────────


class NodeTypes:
    TARGET = "target"
    COMPANY = "company"
    DOMAIN = "domain"
    SUBDOMAIN = "subdomain"
    ENDPOINT = "endpoint"
    FINDING = "finding"
    REPORT = "report"
    REWARD = "reward"
    INVOICE = "invoice"
    EVENT = "event"
    DECISION = "decision"
    CVE = "cve"
    TECHNOLOGY = "technology"
    WALLET = "wallet"
    EXCHANGE = "exchange"
    BROKER = "broker"
    MARKET = "market"
    USER = "user"
    WORKFLOW = "workflow"
    PLAYBOOK = "playbook"
    TOOL = "tool"
    SERVICE = "service"


class EdgeTypes:
    HAS_FINDING = "has_finding"
    HAS_REPORT = "has_report"
    HAS_REWARD = "has_reward"
    HAS_INVOICE = "has_invoice"
    HAS_DECISION = "has_decision"
    HAS_CVE = "has_cve"
    HAS_TECHNOLOGY = "has_technology"
    HAS_SUBDOMAIN = "has_subdomain"
    HAS_ENDPOINT = "has_endpoint"
    HAS_EVENT = "has_event"
    HAS_WALLET = "has_wallet"
    BELONGS_TO = "belongs_to"
    DETECTED_ON = "detected_on"
    GENERATED = "generated"
    PAYS = "pays"
    USES = "uses"
    RELATED_TO = "related_to"
    TRIGGERED = "triggered"
    PRODUCES = "produces"
    LEADS_TO = "leads_to"
    FEEDS_INTO = "feeds_into"


class KnowledgeGraph:
    """Unified knowledge graph connecting all ORION entities.

    Provides backward-compatible API wrapping the in-memory KnowledgeGraphManager.
    """

    def __init__(self, db_id: str | None = None) -> None:
        self._manager = KnowledgeGraphManager()
        self._db_id = db_id or "knowledge_graph"

    def _node_to_dict(self, node: KnowledgeGraphNode | None) -> dict[str, Any]:
        if node is None:
            return {}
        return {
            "id": node.node_id,
            "node_type": node.node_type,
            "label": node.label,
            "metadata": node.metadata,
            "created_at": node.created_at,
            "updated_at": node.updated_at,
        }

    def _edge_to_dict(self, edge: KnowledgeGraphEdge) -> dict[str, Any]:
        return {
            "id": edge.edge_id,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "type": edge.relation_type,
            "weight": 1.0,
            "metadata": edge.metadata,
        }

    # ── Node operations ─────────────────────────────────────────

    def add_node(
        self,
        node_type: str,
        name: str,
        properties: dict[str, Any] | None = None,
        node_id: str | None = None,
        display_label: str | None = None,
        source: str = "",
    ) -> KnowledgeGraphNode:
        """Add a node. If node_id is provided, upserts."""
        node_id = node_id or f"{node_type}:{name}:{uuid.uuid4().hex[:8]}"
        props = properties or {}
        now = datetime.now(UTC).isoformat()

        if node_id in self._manager.nodes:
            existing = self._manager.nodes[node_id]
            existing.label = name
            existing.metadata = props or existing.metadata
            existing.updated_at = datetime.now(UTC).isoformat()
            return existing

        node = KnowledgeGraphNode(
            node_id=node_id,
            node_type=node_type,
            label=name,
            metadata=props or {},
            created_at=now,
            updated_at=now,
        )
        self._manager.add_node(node)
        return node

    def get_node(self, node_id: str) -> KnowledgeGraphNode | None:
        """Get a node by ID."""
        return self._manager.get_node(node_id)

    def find_nodes(
        self,
        node_type: str | None = None,
        name_pattern: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KnowledgeGraphNode]:
        """Find nodes by type and/or name pattern."""
        return self._manager.find_nodes(node_type, name_pattern, limit, offset)

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its edges. Returns True if deleted."""
        if node_id not in self._manager.nodes:
            return False
        # Remove edges connected to this node
        edges_to_remove = [
            eid for eid, edge in self._manager.edges.items() if edge.source_id == node_id or edge.target_id == node_id
        ]
        for eid in edges_to_remove:
            del self._manager.edges[eid]
            # Update adjacency
            for adj_set in self._manager._adj.values():
                adj_set.discard(node_id)
            if node_id in self._manager._adj:
                del self._manager._adj[node_id]

        del self._manager.nodes[node_id]
        return True

    # ── Edge operations ─────────────────────────────────────────

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str = EdgeTypes.RELATED_TO,
        weight: float = 1.0,
        properties: dict[str, Any] | None = None,
    ) -> KnowledgeGraphEdge | None:
        """Add a directed edge between two nodes."""
        source = self._manager.get_node(source_id)
        target = self._manager.get_node(target_id)
        if not source or not target:
            logger.warning("Cannot add edge: node not found (%s → %s)", source_id, target_id)
            return None

        edge_id = f"rel::{source_id}::{target_id}::{edge_type}"
        edge = KnowledgeGraphEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=edge_type,
            metadata=properties or {},
            confidence=weight,
        )
        self._manager.add_edge(edge)
        return edge

    def get_edges(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        edge_type: str | None = None,
        limit: int = 100,
    ) -> list[KnowledgeGraphEdge]:
        """Get edges, optionally filtered."""
        return self._manager.get_edges(source_id, target_id, edge_type, limit)

    def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge. Returns True if deleted."""
        if edge_id in self._manager.edges:
            edge = self._manager.edges[edge_id]
            # Update adjacency
            self._manager._adj[edge.source_id].discard(edge.target_id)
            self._manager._adj[edge.target_id].discard(edge.source_id)
            del self._manager.edges[edge_id]
            return True
        return False

    # ── Traversal ───────────────────────────────────────────────

    def get_neighbors(
        self,
        node_id: str,
        edge_type: str | None = None,
        direction: str = "both",
        max_depth: int = 1,
    ) -> list[dict[str, Any]]:
        """Get neighboring nodes up to a depth, optionally filtered by edge type.

        Returns list of {node, edge, depth}.
        """
        return self._manager.get_neighbors(node_id, edge_type, direction, max_depth)

    def get_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 6,
    ) -> list[list[dict[str, Any]]]:
        """Find all paths between two nodes (BFS, up to max_depth).

        Returns list of paths, each path is a list of {node, edge} steps.
        """
        if start_id == end_id:
            node = self._manager.get_node(start_id)
            return (
                [[{"node": self._node_to_dict(self._manager.get_node(start_id))}]]
                if self._manager.get_node(start_id)
                else []
            )

        # BFS with path tracking
        visited: set[str] = set()
        queue: deque[tuple[str, list[dict[str, Any]]]] = deque()
        queue.append((start_id, []))
        visited.add(start_id)
        paths: list[list[dict[str, Any]]] = []

        while queue and len(paths) < 10:
            current_id, path = queue.popleft()
            if len(path) >= max_depth:
                continue

            neighbors = self.get_neighbors(current_id, direction="outgoing", max_depth=1)
            for entry in neighbors:
                neighbor_id = entry["node"]["id"]
                step = {
                    "node": entry["node"],
                    "edge": entry["edge"],
                }
                new_path = path + [step]

                if neighbor_id == end_id:
                    paths.append(new_path)
                elif neighbor_id not in visited and len(new_path) < max_depth:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, new_path))

        return paths

    def get_subgraph(
        self,
        center_id: str | None = None,
        node_types: list[str] | None = None,
        depth: int = 2,
        limit: int = 500,
    ) -> dict[str, Any]:
        """Get a subgraph centered on a node or filtered by types.

        Returns {"nodes": [...], "edges": [...], "center": center_id}.
        """
        node_ids: set[str] = set()
        nodes_dict: dict[str, Any] = {}
        edges_list: list[dict[str, Any]] = []

        if center_id:
            center = self._manager.get_node(center_id)
            if center:
                node_ids.add(center_id)
                nodes_dict[center_id] = self._node_to_dict(self._manager.get_node(center_id))
                # Expand outward
                neighbors = self.get_neighbors(center_id, max_depth=depth)
                for entry in neighbors:
                    nid = entry["node"]["id"]
                    node_ids.add(nid)
                    nodes_dict[nid] = entry["node"]
                    edges_list.append(entry["edge"])

        if node_types:
            for node in self._manager.nodes.values():
                if node.node_type in node_types and node.node_id not in node_ids:
                    node_ids.add(node.node_id)
                    nodes_dict[node.node_id] = self._node_to_dict(node)

        if not node_ids:
            for node in list(self._manager.nodes.values())[:limit]:
                node_ids.add(node.node_id)
                nodes_dict[node.node_id] = self._node_to_dict(node)

        # Collect edges
        for edge in self._manager.edges.values():
            if edge.source_id in node_ids and edge.target_id in node_ids:
                edges_list.append(self._edge_to_dict(edge))

        return {
            "nodes": list(nodes_dict.values()),
            "edges": edges_list,
            "center": center_id,
            "total_nodes": len(nodes_dict),
            "total_edges": len(edges_list),
        }

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics."""
        type_counts: dict[str, int] = {}
        edge_type_counts: dict[str, int] = {}
        for node in self._manager.nodes.values():
            type_counts[node.node_type] = type_counts.get(node.node_type, 0) + 1
        for edge in self._manager.edges.values():
            edge_type_counts[edge.relation_type] = edge_type_counts.get(edge.relation_type, 0) + 1

        return {
            "total_nodes": len(self._manager.nodes),
            "total_edges": len(self._manager.edges),
            "nodes_by_type": type_counts,
            "edges_by_type": edge_type_counts,
        }

    def record_finding(
        self, target_id: str | None, finding_id: str, finding_name: str, severity: str
    ) -> KnowledgeGraphNode:
        """Add a finding node and connect it to a target (if target_id is provided)."""
        finding = self.add_node(
            NodeTypes.FINDING,
            finding_name,
            {"severity": severity, "finding_id": finding_id},
            node_id=finding_id,
        )
        if target_id and target_id != "orphan":
            self.add_edge(target_id, finding.node_id, EdgeTypes.HAS_FINDING)
        return finding

    def record_report(self, finding_id: str, report_id: str, report_name: str) -> KnowledgeGraphNode:
        """Add a report node and connect it to a finding."""
        report = self.add_node(
            NodeTypes.REPORT,
            report_name,
            {"report_id": report_id},
            node_id=report_id,
        )
        self.add_edge(finding_id, report.node_id, EdgeTypes.GENERATED)
        return report

    def record_decision(self, decision: dict[str, Any]) -> KnowledgeGraphNode:
        """Add a decision node."""
        return self.add_node(
            NodeTypes.DECISION,
            f"Decision: {decision.get('reason', '')[:80]}",
            decision,
            node_id=decision.get("decision_id"),
            source="copilot",
        )

    def search_nodes(self, query: str, limit: int = 20) -> list[KnowledgeGraphNode]:
        """Search nodes by label or metadata."""
        results = []
        lower_query = query.lower()
        for node in self._manager.nodes.values():
            if lower_query in node.label.lower() or lower_query in str(node.metadata).lower():
                results.append(node)
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def _node_to_dict(node: KnowledgeGraphNode | None) -> dict[str, Any]:
        if node is None:
            return {}
        return {
            "id": node.node_id,
            "node_type": node.node_type,
            "label": node.label,
            "metadata": node.metadata,
            "created_at": node.created_at,
            "updated_at": node.updated_at,
        }

    @staticmethod
    def _edge_to_dict(edge: KnowledgeGraphEdge) -> dict[str, Any]:
        return {
            "id": edge.edge_id,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "type": edge.relation_type,
            "weight": edge.confidence,
            "metadata": edge.metadata,
        }


# ── Singleton ────────────────────────────────────────────────

_graph: KnowledgeGraph | None = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph()
    return _graph


def reset_knowledge_graph() -> None:
    global _graph
    _graph = None
