"""Knowledge Graph — unified graph connecting all ORION entities.

Relates targets, companies, findings, reports, rewards, invoices, events,
decisions, CVEs, technologies, wallets, exchanges, and everything else.

Usage:

    from core.knowledge.graph import get_knowledge_graph

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

import json
import logging
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from core.database.manager import get_db_manager
from core.knowledge.models import Base, KGEdge, KGNode

logger = logging.getLogger("orion.core.knowledge.graph")

DB_ID = "knowledge_graph"

# ── Node type constants ────────────────────────────────────────


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


# ── Edge type constants ────────────────────────────────────────


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


# ── Knowledge Graph ────────────────────────────────────────────


class KnowledgeGraph:
    """Unified knowledge graph connecting all ORION entities."""

    def __init__(self, db_id: str | None = None) -> None:
        self._db_id = db_id or DB_ID
        self._ensure_db()

    # ── Node operations ─────────────────────────────────────────

    def add_node(
        self,
        node_type: str,
        name: str,
        properties: dict[str, Any] | None = None,
        node_id: str | None = None,
        display_label: str | None = None,
        source: str = "",
    ) -> KGNode:
        """Add a node. If node_id is provided, upserts."""
        node_id = node_id or self._new_id(node_type, name)
        props_json = json.dumps(properties or {})
        now = datetime.now(UTC)
        session = self._session()
        try:
            existing = session.get(KGNode, node_id)
            if existing:
                existing.name = name
                existing.display_label = display_label or name
                existing.properties = props_json
                existing.source = source or existing.source
                existing.updated_at = now
                session.commit()
                session.refresh(existing)
                logger.debug("Node updated: %s (%s)", node_id, node_type)
                return existing
            node = KGNode(
                id=node_id,
                node_type=node_type,
                name=name,
                display_label=display_label or name,
                properties=props_json,
                source=source,
                created_at=now,
                updated_at=now,
            )
            session.add(node)
            session.commit()
            session.refresh(node)
            logger.debug("Node added: %s (%s)", node_id, node_type)
            return node
        except Exception as exc:
            session.rollback()
            logger.error("Failed to add node: %s", exc)
            raise
        finally:
            session.close()

    def get_node(self, node_id: str) -> KGNode | None:
        """Get a node by ID."""
        session = self._session()
        try:
            return session.get(KGNode, node_id)
        finally:
            session.close()

    def find_nodes(
        self,
        node_type: str | None = None,
        name_pattern: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KGNode]:
        """Find nodes by type and/or name pattern."""
        session = self._session()
        try:
            query = session.query(KGNode)
            if node_type:
                query = query.filter(KGNode.node_type == node_type)
            if name_pattern:
                query = query.filter(KGNode.name.ilike(f"%{name_pattern}%"))
            return query.order_by(KGNode.updated_at.desc()).limit(limit).offset(offset).all()
        finally:
            session.close()

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its edges. Returns True if deleted."""
        session = self._session()
        try:
            node = session.get(KGNode, node_id)
            if not node:
                return False
            # Delete connected edges first
            session.query(KGEdge).filter(or_(KGEdge.source_id == node_id, KGEdge.target_id == node_id)).delete()
            session.delete(node)
            session.commit()
            logger.debug("Node deleted: %s", node_id)
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ── Edge operations ─────────────────────────────────────────

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str = EdgeTypes.RELATED_TO,
        weight: float = 1.0,
        properties: dict[str, Any] | None = None,
    ) -> KGEdge | None:
        """Add a directed edge between two nodes."""
        session = self._session()
        try:
            source = session.get(KGNode, source_id)
            target = session.get(KGNode, target_id)
            if not source or not target:
                logger.warning("Cannot add edge: node not found (%s → %s)", source_id, target_id)
                return None
            edge = KGEdge(
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type,
                weight=weight,
                properties=json.dumps(properties or {}),
                created_at=datetime.now(UTC),
            )
            session.add(edge)
            session.commit()
            session.refresh(edge)
            logger.debug("Edge added: %s → %s (%s, w=%.2f)", source_id, target_id, edge_type, weight)
            return edge
        except Exception as exc:
            session.rollback()
            logger.error("Failed to add edge: %s", exc)
            raise
        finally:
            session.close()

    def get_edges(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        edge_type: str | None = None,
        limit: int = 100,
    ) -> list[KGEdge]:
        """Get edges, optionally filtered."""
        session = self._session()
        try:
            query = session.query(KGEdge)
            if source_id:
                query = query.filter(KGEdge.source_id == source_id)
            if target_id:
                query = query.filter(KGEdge.target_id == target_id)
            if edge_type:
                query = query.filter(KGEdge.edge_type == edge_type)
            return query.order_by(KGEdge.created_at.desc()).limit(limit).all()
        finally:
            session.close()

    def delete_edge(self, edge_id: int) -> bool:
        """Delete an edge. Returns True if deleted."""
        session = self._session()
        try:
            edge = session.get(KGEdge, edge_id)
            if not edge:
                return False
            session.delete(edge)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

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
        visited: set[str] = set()
        results: list[dict[str, Any]] = []
        queue: deque[tuple[str, int]] = deque()
        queue.append((node_id, 0))
        visited.add(node_id)

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            session = self._session()
            try:
                edges = self._get_neighbor_edges(session, current_id, edge_type, direction)
                for edge in edges:
                    neighbor_id = edge.target_id if edge.source_id == current_id else edge.source_id
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        neighbor = session.get(KGNode, neighbor_id)
                        if neighbor:
                            entry = {
                                "node": self._node_to_dict(neighbor),
                                "edge": {
                                    "id": edge.id,
                                    "type": edge.edge_type,
                                    "weight": edge.weight,
                                    "direction": "outgoing" if edge.source_id == current_id else "incoming",
                                },
                                "depth": depth + 1,
                            }
                            results.append(entry)
                            queue.append((neighbor_id, depth + 1))
            finally:
                session.close()

        return results

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
            return [[{"node": self._node_to_dict(self.get_node(start_id))}]]

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

            session = self._session()
            try:
                edges = self._get_neighbor_edges(session, current_id)
                for edge in edges:
                    neighbor_id = edge.target_id if edge.source_id == current_id else edge.source_id

                    step = {
                        "node": self._node_to_dict(session.get(KGNode, neighbor_id)),
                        "edge": {
                            "id": edge.id,
                            "type": edge.edge_type,
                            "weight": edge.weight,
                            "direction": "outgoing" if edge.source_id == current_id else "incoming",
                        },
                    }
                    new_path = path + [step]

                    if neighbor_id == end_id:
                        paths.append(new_path)
                    elif neighbor_id not in visited and len(new_path) < max_depth:
                        visited.add(neighbor_id)
                        queue.append((neighbor_id, new_path))
            finally:
                session.close()

        return paths

    # ── Subgraph ────────────────────────────────────────────────

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
            center = self.get_node(center_id)
            if center:
                node_ids.add(center_id)
                nodes_dict[center_id] = self._node_to_dict(center)
                # Expand outward
                neighbors = self.get_neighbors(center_id, max_depth=depth)
                for entry in neighbors:
                    nid = entry["node"]["id"]
                    node_ids.add(nid)
                    nodes_dict[nid] = entry["node"]
                    edges_list.append(entry["edge"])

        if node_types:
            session = self._session()
            try:
                nodes = session.query(KGNode).filter(KGNode.node_type.in_(node_types)).limit(limit).all()
                for n in nodes:
                    if n.id not in node_ids:
                        node_ids.add(n.id)
                        nodes_dict[n.id] = self._node_to_dict(n)
            finally:
                session.close()

        # If no center or filter, return recent nodes
        if not node_ids:
            session = self._session()
            try:
                nodes = session.query(KGNode).order_by(KGNode.updated_at.desc()).limit(limit).all()
                for n in nodes:
                    node_ids.add(n.id)
                    nodes_dict[n.id] = self._node_to_dict(n)
            finally:
                session.close()

        return {
            "nodes": list(nodes_dict.values()),
            "edges": edges_list,
            "center": center_id,
            "total_nodes": len(nodes_dict),
            "total_edges": len(edges_list),
        }

    # ── Stats ───────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics."""
        session = self._session()
        try:
            total_nodes = session.query(KGNode).count()
            total_edges = session.query(KGEdge).count()
            from sqlalchemy import func

            type_counts = (
                session.query(KGNode.node_type, func.count(KGNode.id))
                .group_by(KGNode.node_type)
                .order_by(func.count(KGNode.id).desc())
                .limit(20)
                .all()
            )
            edge_type_counts = (
                session.query(KGEdge.edge_type, func.count(KGEdge.id))
                .group_by(KGEdge.edge_type)
                .order_by(func.count(KGEdge.id).desc())
                .limit(10)
                .all()
            )
            return {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "nodes_by_type": {row[0]: row[1] for row in type_counts},
                "edges_by_type": {row[0]: row[1] for row in edge_type_counts},
            }
        finally:
            session.close()

    # ── Convenience: add with edges ─────────────────────────────

    def record_finding(self, target_id: str | None, finding_id: str, finding_name: str, severity: str) -> KGNode:
        """Add a finding node and connect it to a target (if target_id is provided)."""
        finding = self.add_node(
            NodeTypes.FINDING,
            finding_name,
            {"severity": severity, "finding_id": finding_id},
            node_id=finding_id,
        )
        if target_id and target_id != "orphan":
            self.add_edge(target_id, finding.id, EdgeTypes.HAS_FINDING)
        return finding

    def record_report(self, finding_id: str, report_id: str, report_name: str) -> KGNode:
        """Add a report node and connect it to a finding."""
        report = self.add_node(
            NodeTypes.REPORT,
            report_name,
            {"report_id": report_id},
            node_id=report_id,
        )
        self.add_edge(finding_id, report.id, EdgeTypes.GENERATED)
        return report

    def record_decision(self, decision: dict[str, Any]) -> KGNode:
        """Add a decision node."""
        return self.add_node(
            NodeTypes.DECISION,
            f"Decision: {decision.get('reason', '')[:80]}",
            decision,
            node_id=decision.get("decision_id"),
            source="copilot",
        )

    # ── Internal ────────────────────────────────────────────────

    def _ensure_db(self) -> None:
        mgr = get_db_manager()
        if self._db_id not in mgr.list_databases():
            db_file = f"knowledge_graph_{self._db_id}.db"
            mgr.register(self._db_id, db_file)
        mgr.run_migrations(self._db_id, Base)

    def _session(self) -> Session:
        return get_db_manager().get_session(self._db_id)

    @staticmethod
    def _new_id(node_type: str, name: str) -> str:
        raw = f"{node_type}:{name}:{uuid.uuid4().hex[:8]}"
        return raw

    @staticmethod
    def _node_to_dict(node: KGNode | None) -> dict[str, Any]:
        if node is None:
            return {}
        props = {}
        try:
            props = json.loads(node.properties) if node.properties else {}
        except (json.JSONDecodeError, TypeError):
            props = {}
        return {
            "id": node.id,
            "node_type": node.node_type,
            "name": node.name,
            "display_label": node.display_label or node.name,
            "properties": props,
            "source": node.source or "",
            "created_at": node.created_at.isoformat() if node.created_at else "",
            "updated_at": node.updated_at.isoformat() if node.updated_at else "",
        }

    @staticmethod
    def _get_neighbor_edges(
        session: Session,
        node_id: str,
        edge_type: str | None = None,
        direction: str = "both",
    ) -> list[KGEdge]:
        query = session.query(KGEdge).filter(or_(KGEdge.source_id == node_id, KGEdge.target_id == node_id))
        if edge_type:
            query = query.filter(KGEdge.edge_type == edge_type)
        if direction == "outgoing":
            query = session.query(KGEdge).filter(KGEdge.source_id == node_id)
        elif direction == "incoming":
            query = session.query(KGEdge).filter(KGEdge.target_id == node_id)
        return query.all()


# ── Singleton ────────────────────────────────────────

_graph: KnowledgeGraph | None = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph()
    return _graph


def reset_knowledge_graph() -> None:
    global _graph
    _graph = None
