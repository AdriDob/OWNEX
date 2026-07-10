"""Tests for Evidence Graph — persistence, balance, integration."""

from __future__ import annotations

import pytest

from core.evidence_graph.graph import EvidenceGraph, get_evidence_graph


@pytest.fixture(autouse=True)
def _cleanup():
    """Clean the evidence graph between tests."""
    graph = get_evidence_graph()
    for hid in graph.get_all_hypotheses():
        graph.delete_hypothesis(hid)
    yield


@pytest.fixture
def graph() -> EvidenceGraph:
    return get_evidence_graph()


class TestEvidenceNode:
    def test_add_node(self, graph: EvidenceGraph) -> None:
        nid = graph.add_node(
            hypothesis_id="hyp-001",
            type="for",
            description="Direct evidence of IDOR",
            weight=0.9,
            source="manual_test",
            confidence=0.85,
        )
        assert isinstance(nid, int)
        assert nid > 0

    def test_add_node_with_metadata(self, graph: EvidenceGraph) -> None:
        nid = graph.add_node(
            hypothesis_id="hyp-002",
            type="against",
            description="Public endpoint, not IDOR",
            weight=0.7,
            source="automated",
            confidence=0.6,
            metadata={"test_type": "ssrf_check", "endpoint": "/api/public"},
        )
        assert nid > 0

    def test_add_node_defaults(self, graph: EvidenceGraph) -> None:
        nid = graph.add_node(hypothesis_id="hyp-003", description="Minimal node")
        assert nid > 0

    def test_add_node_duplicate_hypothesis(self, graph: EvidenceGraph) -> None:
        graph.add_node(hypothesis_id="hyp-004", type="for", description="First")
        graph.add_node(hypothesis_id="hyp-004", type="for", description="Second")
        evidence = graph.get_evidence("hyp-004")
        assert len(evidence["for"]) == 2


class TestEvidenceEdge:
    def test_add_edge(self, graph: EvidenceGraph) -> None:
        nid1 = graph.add_node(hypothesis_id="hyp-005", description="Node A")
        nid2 = graph.add_node(hypothesis_id="hyp-005", description="Node B")
        eid = graph.add_edge(nid1, nid2, edge_type="supports", weight=0.8)
        assert isinstance(eid, int)
        assert eid > 0

    def test_edge_different_hypotheses(self, graph: EvidenceGraph) -> None:
        nid1 = graph.add_node(hypothesis_id="hyp-006", description="Node A")
        nid2 = graph.add_node(hypothesis_id="hyp-007", description="Node B")
        eid = graph.add_edge(nid1, nid2, edge_type="contradicts")
        assert eid > 0


class TestGetEvidence:
    def test_get_evidence_empty(self, graph: EvidenceGraph) -> None:
        evidence = graph.get_evidence("nonexistent")
        assert evidence == {"for": [], "against": [], "neutral": []}

    def test_get_evidence_split(self, graph: EvidenceGraph) -> None:
        graph.add_node(hypothesis_id="hyp-008", type="for", description="Pro 1")
        graph.add_node(hypothesis_id="hyp-008", type="for", description="Pro 2")
        graph.add_node(hypothesis_id="hyp-008", type="against", description="Con 1")
        graph.add_node(hypothesis_id="hyp-008", type="neutral", description="Neutral")

        evidence = graph.get_evidence("hyp-008")
        assert len(evidence["for"]) == 2
        assert len(evidence["against"]) == 1
        assert len(evidence["neutral"]) == 1

    def test_get_evidence_for(self, graph: EvidenceGraph) -> None:
        graph.add_node(hypothesis_id="hyp-009", type="for", description="Pro")
        graph.add_node(hypothesis_id="hyp-009", type="against", description="Con")
        for_ev = graph.get_evidence_for("hyp-009")
        assert len(for_ev) == 1
        assert for_ev[0]["type"] == "for"

    def test_get_evidence_against(self, graph: EvidenceGraph) -> None:
        graph.add_node(hypothesis_id="hyp-010", type="against", description="Con")
        against = graph.get_evidence_against("hyp-010")
        assert len(against) == 1
        assert against[0]["type"] == "against"


class TestBalance:
    def test_balance_empty(self, graph: EvidenceGraph) -> None:
        bal = graph.get_balance("nonexistent")
        assert bal["net_score"] == 0.0
        assert bal["for_count"] == 0
        assert bal["against_count"] == 0

    def test_balance_net_positive(self, graph: EvidenceGraph) -> None:
        graph.add_node("hyp-011", "for", "Strong evidence", weight=0.9, confidence=0.95)
        graph.add_node("hyp-011", "against", "Weak counter", weight=0.3, confidence=0.4)
        bal = graph.get_balance("hyp-011")
        assert bal["net_score"] > 0
        assert bal["for_count"] == 1
        assert bal["against_count"] == 1

    def test_balance_net_negative(self, graph: EvidenceGraph) -> None:
        graph.add_node("hyp-012", "against", "Strong counter", weight=0.9, confidence=0.95)
        graph.add_node("hyp-012", "against", "Another counter", weight=0.8, confidence=0.9)
        graph.add_node("hyp-012", "for", "Weak evidence", weight=0.2, confidence=0.3)
        bal = graph.get_balance("hyp-012")
        assert bal["net_score"] < 0
        assert bal["against_count"] == 2

    def test_balance_format(self, graph: EvidenceGraph) -> None:
        graph.add_node("hyp-013", "for", "Evidence", weight=0.5, confidence=0.5)
        bal = graph.get_balance("hyp-013")
        assert "hypothesis_id" in bal
        assert "for_weighted" in bal
        assert "against_weighted" in bal
        assert "net_score" in bal
        assert "total_weighted" in bal


class TestRecordFromVerdict:
    def test_record_confirmed(self, graph: EvidenceGraph) -> None:
        result = graph.record_from_verdict(
            hypothesis_id="hyp-020",
            verdict_status="confirmed",
            confidence=0.88,
        )
        assert len(result["node_ids"]) == 1
        evidence = graph.get_evidence_for("hyp-020")
        assert len(evidence) == 1
        assert evidence[0]["source"] == "validation_pipeline"

    def test_record_rejected(self, graph: EvidenceGraph) -> None:
        result = graph.record_from_verdict(
            hypothesis_id="hyp-021",
            verdict_status="rejected",
            confidence=0.75,
        )
        assert len(result["node_ids"]) == 1
        evidence = graph.get_evidence_against("hyp-021")
        assert len(evidence) == 1

    def test_record_with_alternatives(self, graph: EvidenceGraph) -> None:
        alternatives = [
            {"description": "Public endpoint", "weight": 0.7},
            {"description": "Cached response", "weight": 0.3},
        ]
        result = graph.record_from_verdict(
            hypothesis_id="hyp-022",
            verdict_status="confirmed",
            confidence=0.80,
            alternatives=alternatives,
        )
        assert len(result["node_ids"]) == 3  # 1 confirmed + 2 alternatives
        evidence = graph.get_evidence("hyp-022")
        assert len(evidence["for"]) == 1
        assert len(evidence["against"]) == 2

    def test_record_inconclusive(self, graph: EvidenceGraph) -> None:
        result = graph.record_from_verdict(
            hypothesis_id="hyp-023",
            verdict_status="inconclusive",
            confidence=0.5,
        )
        assert len(result["node_ids"]) == 0


class TestRecordFromCopilot:
    def test_record_with_inconsistencies(self, graph: EvidenceGraph) -> None:
        nid = graph.record_from_copilot(
            "hyp-030",
            {
                "confidence": 0.6,
                "inconsistencies": ["Missing evidence", "Low reproducibility"],
            },
        )
        assert isinstance(nid, int)
        evidence = graph.get_evidence_against("hyp-030")
        assert len(evidence) == 1
        assert "Missing evidence" in evidence[0]["description"]

    def test_record_clean(self, graph: EvidenceGraph) -> None:
        graph.record_from_copilot(
            "hyp-031",
            {"confidence": 0.9, "inconsistencies": []},
        )
        evidence = graph.get_evidence_for("hyp-031")
        assert len(evidence) == 1


class TestDeleteAndStats:
    def test_delete_hypothesis(self, graph: EvidenceGraph) -> None:
        graph.add_node("hyp-040", "for", "Evidence")
        graph.add_node("hyp-040", "against", "Counter")
        assert graph.delete_hypothesis("hyp-040") is True
        assert graph.get_balance("hyp-040")["for_count"] == 0

    def test_delete_nonexistent(self, graph: EvidenceGraph) -> None:
        assert graph.delete_hypothesis("nonexistent") is False

    def test_get_all_hypotheses(self, graph: EvidenceGraph) -> None:
        graph.add_node("hyp-050", "for", "A")
        graph.add_node("hyp-051", "for", "B")
        hypotheses = graph.get_all_hypotheses()
        assert "hyp-050" in hypotheses
        assert "hyp-051" in hypotheses

    def test_get_stats(self, graph: EvidenceGraph) -> None:
        graph.add_node("hyp-060", "for", "A")
        graph.add_node("hyp-060", "against", "B")
        graph.add_node("hyp-061", "for", "C")
        stats = graph.get_stats()
        assert stats["total_nodes"] == 3
        assert stats["hypotheses"] == 2
        assert stats["for_count"] == 2
        assert stats["against_count"] == 1


class TestSingleton:
    def test_singleton(self) -> None:
        g1 = get_evidence_graph()
        g2 = get_evidence_graph()
        assert g1 is g2

    def test_singleton_is_instance(self) -> None:
        g = get_evidence_graph()
        assert isinstance(g, EvidenceGraph)


class TestPersistence:
    def test_evidence_survives_multiple_calls(self, graph: EvidenceGraph) -> None:
        graph.add_node("hyp-070", "for", "Persistent evidence")
        g2 = get_evidence_graph()
        evidence = g2.get_evidence("hyp-070")
        assert len(evidence["for"]) == 1

    def test_balance_after_restart(self, graph: EvidenceGraph) -> None:
        graph.add_node("hyp-071", "for", "A", weight=0.8, confidence=0.9)
        graph.add_node("hyp-071", "against", "B", weight=0.6, confidence=0.5)
        # Simulate re-loading from DB
        g2 = get_evidence_graph()
        bal = g2.get_balance("hyp-071")
        assert bal["for_count"] == 1
        assert bal["against_count"] == 1
        assert bal["net_score"] == pytest.approx(0.8 * 0.9 - 0.6 * 0.5)
