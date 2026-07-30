from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="lightrag",
    name="LightRAG Memory",
    version="1.0.0",
    description="Graph-native RAG memory layer. Replaces flat vector search with "
    "relationship-aware retrieval: entities, their connections, and "
    "semantic context are all stored in a queryable knowledge graph. "
    "Powers context-aware reasoning for all OWNEX agents.",
    author="OWNEX",
    icon="BrainCircuit",
    capabilities=[
        Capability(domain="graph_rag_retrieval",
            name="Graph RAG Retrieval",
            description="Retrieve entities and relationships with graph-aware context",
        ),
        Capability(domain="memory_insert",
            name="Memory Insert",
            description="Insert observations, facts, and learnings into the graph memory",
        ),
        Capability(domain="semantic_search",
            name="Semantic Search",
            description="Cross-entity semantic search over all stored knowledge",
        ),
    ],
    hooks={
        "memory_store": "lightrag.hooks.on_memory_store",
        "memory_retrieve": "lightrag.hooks.on_memory_retrieve",
        "context_enrich": "lightrag.hooks.on_context_enrich",
    },
    providers=["lightrag_memory"],
    hot_reloadable=False,
    requires_core="5.0.0",
)
