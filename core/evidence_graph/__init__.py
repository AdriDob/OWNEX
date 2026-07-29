from __future__ import annotations

"""Evidence Graph — persistent for/against evidence per hypothesis.
Each hypothesis stores:
- evidence for / evidence against
- weight, source, timestamp, confidence
- inter-node relationships (edges)
The Copilot queries this to make informed decisions.
"""
from core.evidence_graph.graph import EvidenceGraph, get_evidence_graph

__all__ = [
    "EvidenceGraph",
    "get_evidence_graph",
]
