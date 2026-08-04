from __future__ import annotations

"""Knowledge Graph — unified graph connecting all ORION entities.
Connects targets, companies, findings, reports, rewards, invoices, events,
decisions, CVEs, technologies, wallets, exchanges, and more.
Usage:
    from core.knowledge.graph import get_knowledge_graph, NodeTypes, EdgeTypes
    kg = get_knowledge_graph()
    kg.add_node(NodeTypes.TARGET, "example.com", {"domain": "example.com"})
    kg.add_edge(target_id, finding_id, EdgeTypes.HAS_FINDING)
    neighbors = kg.get_neighbors(target_id)
"""
# ruff: noqa: E402
from core.knowledge.graph import (
    EdgeTypes,
    KGEdge,
    KGNode,
    KnowledgeGraph,
    NodeTypes,
    get_knowledge_graph,
    reset_knowledge_graph,
)

__all__ = [
    "KnowledgeGraph",
    "KGNode",
    "KGEdge",
    "NodeTypes",
    "EdgeTypes",
    "get_knowledge_graph",
    "reset_knowledge_graph",
]
