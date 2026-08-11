"""Evidence Graph — persistent engine for for/against evidence per hypothesis."""

from __future__ import annotations

import json
import logging
from typing import Any

from core.database.manager import get_db_manager
from core.evidence_graph.models import Base, EvidenceEdge, EvidenceNode

logger = logging.getLogger("orion.core.evidence_graph")

DB_ID = "evidence_graph"


def _ensure_db() -> None:
    mgr = get_db_manager()
    if DB_ID not in mgr.list_databases():
        mgr.register(DB_ID, "evidence_graph.db")
    mgr.run_migrations(DB_ID, Base)


class EvidenceGraph:
    """Persistent evidence graph for hypotheses.

    Stores evidence for/against each hypothesis with weight, source,
    confidence, and inter-node relationships.
    """

    def add_node(
        self,
        hypothesis_id: str,
        type: str = "neutral",
        description: str = "",
        weight: float = 0.5,
        source: str = "unknown",
        confidence: float = 0.0,
        origin: str = "core.evidence_graph",
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Add an evidence node. Returns the node ID."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            node = EvidenceNode(
                hypothesis_id=hypothesis_id,
                type=type,
                description=description,
                weight=weight,
                source=source,
                confidence=confidence,
                origin=origin,
                metadata_json=json.dumps(metadata or {}),
            )
            db.add(node)
            db.commit()
            logger.debug("Evidence node added: %d (%s for %s)", node.id, type, hypothesis_id)
            return node.id
        except Exception as exc:
            db.rollback()
            logger.error("Failed to add evidence node: %s", exc)
            raise
        finally:
            db.close()

    def add_edge(
        self,
        from_node_id: int,
        to_node_id: int,
        edge_type: str = "related_to",
        weight: float = 0.5,
    ) -> int:
        """Create a relationship between two evidence nodes. Returns the edge ID."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            edge = EvidenceEdge(
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                edge_type=edge_type,
                weight=weight,
            )
            db.add(edge)
            db.commit()
            logger.debug("Evidence edge added: %d → %d (%s)", from_node_id, to_node_id, edge_type)
            return edge.id
        except Exception as exc:
            db.rollback()
            logger.error("Failed to add evidence edge: %s", exc)
            raise
        finally:
            db.close()

    def get_evidence(self, hypothesis_id: str) -> dict[str, list[dict[str, Any]]]:
        """Get all evidence for a hypothesis, split by type."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            nodes = db.query(EvidenceNode).filter(EvidenceNode.hypothesis_id == hypothesis_id).all()
            result: dict[str, list[dict[str, Any]]] = {"for": [], "against": [], "neutral": []}
            for node in nodes:
                entry = self._node_to_dict(node)
                result.setdefault(node.type, []).append(entry)
            return result
        finally:
            db.close()

    def get_evidence_for(self, hypothesis_id: str) -> list[dict[str, Any]]:
        return self.get_evidence(hypothesis_id).get("for", [])

    def get_evidence_against(self, hypothesis_id: str) -> list[dict[str, Any]]:
        return self.get_evidence(hypothesis_id).get("against", [])

    def get_balance(self, hypothesis_id: str) -> dict[str, Any]:
        """Compute the net evidence balance for a hypothesis."""
        evidence = self.get_evidence(hypothesis_id)
        for_sum = sum(n.get("weight", 0) * n.get("confidence", 0) for n in evidence["for"])
        against = sum(n.get("weight", 0) * n.get("confidence", 0) for n in evidence["against"])
        net = for_sum - against
        total = for_sum + against
        return {
            "hypothesis_id": hypothesis_id,
            "for_weighted": round(for_sum, 4),
            "against_weighted": round(against, 4),
            "net_score": round(net, 4),
            "total_weighted": round(total, 4),
            "for_count": len(evidence["for"]),
            "against_count": len(evidence["against"]),
            "neutral_count": len(evidence["neutral"]),
        }

    def record_from_verdict(
        self,
        hypothesis_id: str,
        verdict_status: str,
        confidence: float,
        alternatives: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[int]]:
        """Record evidence nodes from a verdict's data.

        Returns {node_ids: [id, ...]}.
        """
        node_ids: list[int] = []

        if verdict_status == "confirmed":
            nid = self.add_node(
                hypothesis_id=hypothesis_id,
                type="for",
                description="Validación confirmó la hipótesis",
                weight=confidence,
                source="validation_pipeline",
                confidence=confidence,
                origin="cores.validation",
            )
            node_ids.append(nid)
        elif verdict_status == "rejected":
            nid = self.add_node(
                hypothesis_id=hypothesis_id,
                type="against",
                description="Validación rechazó la hipótesis",
                weight=confidence,
                source="validation_pipeline",
                confidence=confidence,
                origin="cores.validation",
            )
            node_ids.append(nid)

        if alternatives:
            for alt in alternatives:
                alt_desc = alt.get("description", "Explicación alternativa")
                alt_weight = alt.get("weight", 0.5)
                nid = self.add_node(
                    hypothesis_id=hypothesis_id,
                    type="against",
                    description=f"Alternativa: {alt_desc}",
                    weight=alt_weight,
                    source="hypothesis_challenger",
                    confidence=1.0 - alt_weight,
                    origin="cores.validation.challenger",
                )
                node_ids.append(nid)

        return {"node_ids": node_ids}

    def record_from_copilot(
        self,
        hypothesis_id: str,
        analysis_result: dict[str, Any],
    ) -> int:
        """Record an analysis result from the Copilot as an evidence node."""
        inconsistencies = analysis_result.get("inconsistencies", [])
        if inconsistencies:
            desc = "; ".join(inconsistencies[:3])
            return self.add_node(
                hypothesis_id=hypothesis_id,
                type="against",
                description=f"Inconsistencias del Copilot: {desc}",
                weight=0.6,
                source="copilot_analysis",
                confidence=analysis_result.get("confidence", 0.5),
                origin="core.copilot.analyzer",
            )

        return self.add_node(
            hypothesis_id=hypothesis_id,
            type="for",
            description="Copilot analysis passed without inconsistencies",
            weight=analysis_result.get("confidence", 0.5),
            source="copilot_analysis",
            confidence=analysis_result.get("confidence", 0.5),
            origin="core.copilot.analyzer",
        )

    def get_all_hypotheses(self) -> list[str]:
        """Return all hypothesis IDs that have evidence."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            rows = db.query(EvidenceNode.hypothesis_id).distinct().all()
            return [r[0] for r in rows]
        finally:
            db.close()

    def delete_hypothesis(self, hypothesis_id: str) -> bool:
        """Delete all evidence for a hypothesis (edges first, then nodes)."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            node_ids = [
                r[0] for r in db.query(EvidenceNode.id).filter(EvidenceNode.hypothesis_id == hypothesis_id).all()
            ]
            if not node_ids:
                return False
            db.query(EvidenceEdge).filter(EvidenceEdge.from_node_id.in_(node_ids)).delete(synchronize_session=False)
            db.query(EvidenceEdge).filter(EvidenceEdge.to_node_id.in_(node_ids)).delete(synchronize_session=False)
            count = (
                db.query(EvidenceNode)
                .filter(EvidenceNode.hypothesis_id == hypothesis_id)
                .delete(synchronize_session=False)
            )
            db.commit()
            logger.info("Deleted %d evidence nodes (and edges) for %s", count, hypothesis_id)
            return True
        except Exception as exc:
            db.rollback()
            logger.error("Failed to delete evidence: %s", exc)
            return False
        finally:
            db.close()

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate statistics."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            total_nodes = db.query(EvidenceNode).count()
            total_edges = db.query(EvidenceEdge).count()
            hypotheses = db.query(EvidenceNode.hypothesis_id).distinct().count()
            for_count = db.query(EvidenceNode).filter(EvidenceNode.type == "for").count()
            against_count = db.query(EvidenceNode).filter(EvidenceNode.type == "against").count()
            neutral_count = db.query(EvidenceNode).filter(EvidenceNode.type == "neutral").count()
            return {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "hypotheses": hypotheses,
                "for_count": for_count,
                "against_count": against_count,
                "neutral_count": neutral_count,
            }
        finally:
            db.close()

    @staticmethod
    def _node_to_dict(node: EvidenceNode) -> dict[str, Any]:
        return {
            "id": node.id,
            "hypothesis_id": node.hypothesis_id,
            "type": node.type,
            "description": node.description,
            "weight": node.weight,
            "source": node.source,
            "confidence": node.confidence,
            "origin": node.origin,
            "metadata": json.loads(node.metadata_json or "{}"),
            "created_at": str(node.created_at),
        }


_Singleton: EvidenceGraph | None = None


def get_evidence_graph() -> EvidenceGraph:
    global _Singleton
    if _Singleton is None:
        _Singleton = EvidenceGraph()
    return _Singleton
