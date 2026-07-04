"""Knowledge infrastructure for CATEYE.

This package defines a modular, extensible knowledge ingestion and graph
infrastructure for long-term intelligence. It is intentionally connector-agnostic
and prepared to absorb diverse sources such as MITRE CWE, CVE/NVD, OWASP,
PortSwigger Academy, Nuclei templates, payload collections, and bounty platforms.
"""

from .graph import KnowledgeGraphManager
from .manager import KnowledgeManager
from .pipeline import KnowledgeIngestPipeline
from .store import KnowledgeRepository
from .trust import ConfidenceScorer

__all__ = [
    "KnowledgeManager",
    "KnowledgeIngestPipeline",
    "KnowledgeGraphManager",
    "KnowledgeRepository",
    "ConfidenceScorer",
]
