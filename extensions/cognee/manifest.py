from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="cognee",
    name="Cognee Memory Platform",
    version="1.0.0",
    description="AI memory platform with graph + vector hybrid storage. "
    "Automatically discovers relationships between stored facts, "
    "summarizes old memories, and provides retrieval-augmented "
    "generation with full context awareness.",
    author="OWNEX",
    icon="Memory",
    capabilities=[
        Capability(
            domain="cognitive_memory",
            name="Cognitive Memory",
            description="Persistent long-term memory with graph + vector hybrid storage",
        ),
        Capability(
            domain="relationship_discovery",
            name="Relationship Discovery",
            description="Automatic detection of connections between stored knowledge",
        ),
        Capability(
            domain="memory_consolidation",
            name="Memory Consolidation",
            description="Summarize and compress old memories while preserving key facts",
        ),
    ],
    hooks={
        "memory_store": "cognee.hooks.on_memory_store",
        "memory_retrieve": "cognee.hooks.on_memory_retrieve",
        "memory_consolidate": "cognee.hooks.on_memory_consolidate",
    },
    providers=["cognee_memory"],
    hot_reloadable=False,
    requires_core="5.0.0",
)
