"""Tests for Knowledge Graph: nodes, edges, traversal, subgraph, stats."""

from __future__ import annotations

import uuid

from core.knowledge.graph import (
    EdgeTypes,
    KnowledgeGraph,
    NodeTypes,
    get_knowledge_graph,
    reset_knowledge_graph,
)

# ── Helpers ────────────────────────────────────────────────────


def _fresh_kg() -> KnowledgeGraph:
    """Return a KnowledgeGraph instance with a unique DB ID per test call."""
    reset_knowledge_graph()
    # Use a unique id so parallel tests don't collide
    unique = uuid.uuid4().hex[:12]
    return KnowledgeGraph(db_id=f"kg_test_{unique}")


# ── NodeTypes & EdgeTypes ──────────────────────────────────────


def test_node_types_all_defined() -> None:
    assert NodeTypes.TARGET == "target"
    assert NodeTypes.COMPANY == "company"
    assert NodeTypes.FINDING == "finding"
    assert NodeTypes.REPORT == "report"
    assert NodeTypes.DECISION == "decision"
    assert NodeTypes.WORKFLOW == "workflow"
    assert NodeTypes.SERVICE == "service"
    types = {v for k, v in vars(NodeTypes).items() if not k.startswith("_")}
    assert len(types) >= 18


def test_edge_types_all_defined() -> None:
    assert EdgeTypes.HAS_FINDING == "has_finding"
    assert EdgeTypes.HAS_REPORT == "has_report"
    assert EdgeTypes.BELONGS_TO == "belongs_to"
    assert EdgeTypes.GENERATED == "generated"
    assert EdgeTypes.FEEDS_INTO == "feeds_into"
    types = {v for k, v in vars(EdgeTypes).items() if not k.startswith("_")}
    assert len(types) >= 18


# ── Node operations ────────────────────────────────────────────


def test_add_node_basic() -> None:
    kg = _fresh_kg()
    node = kg.add_node(NodeTypes.TARGET, "example.com", {"domain": "example.com"})
    assert node.id is not None
    assert node.node_type == NodeTypes.TARGET
    assert node.name == "example.com"
    assert node.source == ""


def test_add_node_with_properties() -> None:
    kg = _fresh_kg()
    props = {"domain": "test.com", "ip": "1.2.3.4", "tags": ["web", "api"]}
    node = kg.add_node(NodeTypes.TARGET, "test-target", props, source="recon")
    assert node.node_type == NodeTypes.TARGET
    assert node.source == "recon"
    # re-read to verify persistence
    fetched = kg.get_node(node.id)
    assert fetched is not None
    assert fetched.node_type == NodeTypes.TARGET


def test_add_node_with_explicit_id() -> None:
    kg = _fresh_kg()
    node = kg.add_node(NodeTypes.FINDING, "IDOR in /api/users", node_id="finding-001")
    assert node.id == "finding-001"
    fetched = kg.get_node("finding-001")
    assert fetched is not None
    assert fetched.name == "IDOR in /api/users"


def test_add_node_upsert() -> None:
    kg = _fresh_kg()
    n1 = kg.add_node(NodeTypes.TARGET, "upsert-example", node_id="upsert-1")
    assert n1.name == "upsert-example"
    n2 = kg.add_node(NodeTypes.TARGET, "updated-name", node_id="upsert-1")
    assert n2.name == "updated-name"
    assert n2.id == n1.id


def test_get_node_not_found() -> None:
    kg = _fresh_kg()
    assert kg.get_node("nonexistent") is None


def test_find_nodes_by_type() -> None:
    kg = _fresh_kg()
    kg.add_node(NodeTypes.TARGET, "a.com")
    kg.add_node(NodeTypes.FINDING, "bug-1")
    kg.add_node(NodeTypes.TARGET, "b.com")
    targets = kg.find_nodes(node_type=NodeTypes.TARGET)
    assert len(targets) == 2
    findings = kg.find_nodes(node_type=NodeTypes.FINDING)
    assert len(findings) == 1


def test_find_nodes_by_name_pattern() -> None:
    kg = _fresh_kg()
    kg.add_node(NodeTypes.TARGET, "api.example.com")
    kg.add_node(NodeTypes.TARGET, "admin.example.com")
    kg.add_node(NodeTypes.TARGET, "other.com")
    results = kg.find_nodes(name_pattern="example")
    assert len(results) == 2


def test_find_nodes_with_limit() -> None:
    kg = _fresh_kg()
    for i in range(5):
        kg.add_node(NodeTypes.TARGET, f"target-{i}.com")
    results = kg.find_nodes(node_type=NodeTypes.TARGET, limit=3)
    assert len(results) == 3


def test_delete_node() -> None:
    kg = _fresh_kg()
    node = kg.add_node(NodeTypes.TARGET, "delete-me")
    node_id = node.id
    assert kg.get_node(node_id) is not None
    deleted = kg.delete_node(node_id)
    assert deleted is True
    assert kg.get_node(node_id) is None


def test_delete_node_not_found() -> None:
    kg = _fresh_kg()
    assert kg.delete_node("nonexistent") is False


def test_delete_node_cascades_edges() -> None:
    kg = _fresh_kg()
    a = kg.add_node(NodeTypes.TARGET, "a.com")
    b = kg.add_node(NodeTypes.TARGET, "b.com")
    kg.add_edge(a.id, b.id, EdgeTypes.RELATED_TO)
    edges_before = kg.get_edges()
    assert len(edges_before) == 1
    kg.delete_node(a.id)
    edges_after = kg.get_edges()
    assert len(edges_after) == 0


# ── Edge operations ────────────────────────────────────────────


def test_add_edge() -> None:
    kg = _fresh_kg()
    a = kg.add_node(NodeTypes.TARGET, "source")
    b = kg.add_node(NodeTypes.TARGET, "target")
    edge = kg.add_edge(a.id, b.id, EdgeTypes.RELATED_TO, weight=0.8)
    assert edge is not None
    assert edge.edge_type == EdgeTypes.RELATED_TO
    assert edge.weight == 0.8


def test_add_edge_missing_node() -> None:
    kg = _fresh_kg()
    node = kg.add_node(NodeTypes.TARGET, "lonely")
    edge = kg.add_edge(node.id, "nonexistent", EdgeTypes.RELATED_TO)
    assert edge is None


def test_get_edges_filtered() -> None:
    kg = _fresh_kg()
    a = kg.add_node(NodeTypes.TARGET, "a")
    b = kg.add_node(NodeTypes.TARGET, "b")
    c = kg.add_node(NodeTypes.TARGET, "c")
    kg.add_edge(a.id, b.id, "type_a")
    kg.add_edge(a.id, c.id, "type_b")
    edges = kg.get_edges(source_id=a.id)
    assert len(edges) == 2
    type_a = kg.get_edges(source_id=a.id, edge_type="type_a")
    assert len(type_a) == 1
    assert type_a[0].edge_type == "type_a"


def test_delete_edge() -> None:
    kg = _fresh_kg()
    a = kg.add_node(NodeTypes.TARGET, "a")
    b = kg.add_node(NodeTypes.TARGET, "b")
    edge = kg.add_edge(a.id, b.id)
    assert edge is not None
    deleted = kg.delete_edge(edge.id)
    assert deleted is True
    assert kg.delete_edge(999) is False


# ── Traversal ──────────────────────────────────────────────────


def test_get_neighbors_direct() -> None:
    kg = _fresh_kg()
    center = kg.add_node(NodeTypes.TARGET, "center")
    n1 = kg.add_node(NodeTypes.TARGET, "n1")
    n2 = kg.add_node(NodeTypes.TARGET, "n2")
    kg.add_edge(center.id, n1.id)
    kg.add_edge(center.id, n2.id)
    neighbors = kg.get_neighbors(center.id)
    assert len(neighbors) == 2
    assert all(n["depth"] == 1 for n in neighbors)


def test_get_neighbors_by_direction() -> None:
    kg = _fresh_kg()
    a = kg.add_node(NodeTypes.TARGET, "a")
    b = kg.add_node(NodeTypes.TARGET, "b")
    kg.add_edge(a.id, b.id)
    outgoing = kg.get_neighbors(a.id, direction="outgoing")
    assert len(outgoing) == 1
    incoming = kg.get_neighbors(b.id, direction="incoming")
    assert len(incoming) == 1
    no_incoming = kg.get_neighbors(a.id, direction="incoming")
    assert len(no_incoming) == 0


def test_get_neighbors_filtered_by_type() -> None:
    kg = _fresh_kg()
    center = kg.add_node(NodeTypes.TARGET, "center")
    n1 = kg.add_node(NodeTypes.FINDING, "finding")
    n2 = kg.add_node(NodeTypes.TARGET, "other")
    kg.add_edge(center.id, n1.id, EdgeTypes.HAS_FINDING)
    kg.add_edge(center.id, n2.id, EdgeTypes.RELATED_TO)
    finding_edges = kg.get_neighbors(center.id, edge_type=EdgeTypes.HAS_FINDING)
    assert len(finding_edges) == 1
    assert finding_edges[0]["node"]["node_type"] == NodeTypes.FINDING


def test_get_neighbors_with_depth() -> None:
    kg = _fresh_kg()
    a = kg.add_node(NodeTypes.TARGET, "a")
    b = kg.add_node(NodeTypes.TARGET, "b")
    c = kg.add_node(NodeTypes.TARGET, "c")
    kg.add_edge(a.id, b.id)
    kg.add_edge(b.id, c.id)
    depth1 = kg.get_neighbors(a.id, max_depth=1)
    assert len(depth1) == 1
    depth2 = kg.get_neighbors(a.id, max_depth=2)
    assert len(depth2) == 2


def test_get_path_between_nodes() -> None:
    kg = _fresh_kg()
    a = kg.add_node(NodeTypes.TARGET, "a")
    b = kg.add_node(NodeTypes.TARGET, "b")
    c = kg.add_node(NodeTypes.TARGET, "c")
    kg.add_edge(a.id, b.id)
    kg.add_edge(b.id, c.id)
    paths = kg.get_path(a.id, c.id)
    assert len(paths) >= 1
    assert len(paths[0]) == 2  # two steps: a→b, b→c
    assert paths[0][0]["node"]["name"] == "b"
    assert paths[0][1]["node"]["name"] == "c"


def test_get_path_self() -> None:
    kg = _fresh_kg()
    n = kg.add_node(NodeTypes.TARGET, "self")
    paths = kg.get_path(n.id, n.id)
    assert len(paths) == 1
    assert paths[0][0]["node"]["name"] == "self"


def test_get_path_no_path() -> None:
    kg = _fresh_kg()
    a = kg.add_node(NodeTypes.TARGET, "a")
    b = kg.add_node(NodeTypes.TARGET, "b")
    paths = kg.get_path(a.id, b.id)
    assert len(paths) == 0


# ── Subgraph ───────────────────────────────────────────────────


def test_get_subgraph_by_center() -> None:
    kg = _fresh_kg()
    center = kg.add_node(NodeTypes.TARGET, "center")
    n1 = kg.add_node(NodeTypes.FINDING, "finding")
    kg.add_edge(center.id, n1.id)
    sg = kg.get_subgraph(center_id=center.id)
    assert sg["center"] == center.id
    assert len(sg["nodes"]) == 2
    assert len(sg["edges"]) == 1


def test_get_subgraph_by_type() -> None:
    kg = _fresh_kg()
    kg.add_node(NodeTypes.TARGET, "t1")
    kg.add_node(NodeTypes.TARGET, "t2")
    kg.add_node(NodeTypes.FINDING, "f1")
    sg = kg.get_subgraph(node_types=[NodeTypes.TARGET])
    assert sg["total_nodes"] == 2


def test_get_subgraph_empty() -> None:
    kg = _fresh_kg()
    sg = kg.get_subgraph()
    assert sg["total_nodes"] == 0
    assert sg["center"] is None


# ── Stats ──────────────────────────────────────────────────────


def test_get_stats_empty() -> None:
    kg = _fresh_kg()
    stats = kg.get_stats()
    assert stats["total_nodes"] == 0
    assert stats["total_edges"] == 0


def test_get_stats_populated() -> None:
    kg = _fresh_kg()
    t = kg.add_node(NodeTypes.TARGET, "stats-target")
    f = kg.add_node(NodeTypes.FINDING, "stats-finding")
    kg.add_node(NodeTypes.REPORT, "stats-report")
    kg.add_edge(t.id, f.id, EdgeTypes.HAS_FINDING)
    stats = kg.get_stats()
    assert stats["total_nodes"] == 3
    assert stats["total_edges"] == 1
    assert stats["nodes_by_type"].get(NodeTypes.TARGET) == 1
    assert stats["nodes_by_type"].get(NodeTypes.FINDING) == 1
    assert stats["nodes_by_type"].get(NodeTypes.REPORT) == 1


# ── Convenience methods ────────────────────────────────────────


def test_record_finding() -> None:
    kg = _fresh_kg()
    target = kg.add_node(NodeTypes.TARGET, "vuln-app.com")
    finding = kg.record_finding(target.id, "finding-101", "SQL Injection in login", "critical")
    assert finding.node_type == NodeTypes.FINDING
    assert finding.name == "SQL Injection in login"
    # edge should exist
    edges = kg.get_edges(source_id=target.id, edge_type=EdgeTypes.HAS_FINDING)
    assert len(edges) == 1
    assert edges[0].target_id == finding.id


def test_record_report() -> None:
    kg = _fresh_kg()
    target = kg.add_node(NodeTypes.TARGET, "app.com")
    finding = kg.record_finding(target.id, "f-200", "XSS in search", "medium")
    report = kg.record_report(finding.id, "report-001", "Security Report Q3")
    assert report.node_type == NodeTypes.REPORT
    edges = kg.get_edges(source_id=finding.id, edge_type=EdgeTypes.GENERATED)
    assert len(edges) == 1
    assert edges[0].target_id == report.id


def test_record_decision() -> None:
    kg = _fresh_kg()
    decision_data = {
        "decision_id": "dec-001",
        "reason": "Auto-generate report for confirmed finding",
        "priority": "high",
        "confidence": 0.92,
        "finding_id": "f-300",
    }
    node = kg.record_decision(decision_data)
    assert node.node_type == NodeTypes.DECISION
    assert node.source == "copilot"
    fetched = kg.get_node("dec-001")
    assert fetched is not None


# ── Singleton ──────────────────────────────────────────────────


def test_singleton() -> None:
    reset_knowledge_graph()
    kg1 = get_knowledge_graph()
    kg2 = get_knowledge_graph()
    assert kg1 is kg2


def test_reset() -> None:
    reset_knowledge_graph()
    kg1 = get_knowledge_graph()
    reset_knowledge_graph()
    kg3 = get_knowledge_graph()
    assert kg3 is not kg1
