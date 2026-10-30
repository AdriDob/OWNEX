"""
Universal Artifact Store — Versioned, searchable, hash-verified artifact storage.

Provides a unified storage layer for all artifacts with:
- Content-addressable storage (SHA-256)
- Versioned artifacts with immutable history
- Full-text search via SQLite FTS5
- Metadata indexing for fast queries
- Immutable audit trail
"""

from cores.artifact_store.store import (
    Artifact,
    ArtifactStore,
    ArtifactVersion,
    get_artifact_store,
)

__all__ = [
    "Artifact",
    "ArtifactVersion",
    "ArtifactStore",
    "get_artifact_store",
]
