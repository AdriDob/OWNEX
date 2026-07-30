from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="graphiti",
    name="Graphiti Temporal KG",
    version="1.0.0",
    description="Temporal knowledge graph for streaming data. "
    "Dynamically builds entity-relationship graphs from observations "
    "over time, enabling time-aware queries and pattern discovery.",
    author="OWNEX",
    icon="GitGraph",
    capabilities=[
        Capability(
            domain="realtime_kg",
            name="Real-Time Knowledge Graph",
            description="Dynamic entity and relationship detection from data streams",
        ),
        Capability(
            domain="temporal_patterns",
            name="Temporal Pattern Detection",
            description="Discover time-based patterns and trends in observations",
        ),
    ],
    hooks={
        "observation_ingested": "graphiti.hooks.on_observation_ingested",
        "relationship_query": "graphiti.hooks.on_relationship_query",
    },
    providers=["graphiti_kg"],
    hot_reloadable=True,
    requires_core="5.0.0",
)
