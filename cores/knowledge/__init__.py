"""Knowledge infrastructure for ORION.

This package defines a modular, extensible knowledge ingestion and graph
infrastructure for long-term intelligence. It is intentionally connector-agnostic
and prepared to absorb diverse sources such as MITRE CWE, CVE/NVD, OWASP,
PortSwigger Academy, Nuclei templates, payload collections, and bounty platforms.
"""

from .manager import KnowledgeManager
from .pipeline import KnowledgeIngestPipeline
from .trust import ConfidenceScorer
from .graph import KnowledgeGraphManager
from .store import KnowledgeRepository

__all__ = [
    "KnowledgeManager",
    "KnowledgeIngestPipeline",
    "KnowledgeGraphManager",
    "KnowledgeRepository",
    "ConfidenceScorer",
]
