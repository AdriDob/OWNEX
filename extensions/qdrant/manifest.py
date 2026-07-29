from __future__ import annotations

from core.extension.manifest import ExtensionManifest
from core.extension.capabilities import Capability

manifest = ExtensionManifest(
    id="qdrant",
    name="Qdrant Vector Memory",
    version="1.0.0",
    description="Vector-based memory and semantic search plugin. "
                "Replaces SQLite-based memory with persistent vector storage "
                "for semantic recall of projects, solutions, and documentation.",
    author="OWNEX",
    icon="Database",
    capabilities=[
        Capability(
            id="vector_storage",
            name="Vector Storage",
            description="Store and retrieve vector embeddings",
        ),
        Capability(
            id="semantic_search",
            name="Semantic Search",
            description="Search memory by meaning, not just keywords",
        ),
        Capability(
            id="memory_persistence",
            name="Persistent Memory",
            description="Survives process restarts",
        ),
    ],
    hooks={
        "before_ai_reasoning": "qdrant.hooks.before_ai_reasoning",
        "after_startup": "qdrant.hooks.after_startup",
    },
    dependencies=["core/event_bus", "core/credentials/vault.py"],
    providers=["qdrant_memory"],
    hot_reloadable=True,
    requires_core="5.0.0",
)
