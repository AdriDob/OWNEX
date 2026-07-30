from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="graphify",
    name="Graphify Code KG",
    version="1.0.0",
    description="Turn any codebase into a queryable knowledge graph. "
    "Uses deterministic AST parsing (Tree-sitter) to build a precise, "
    "no-hallucination graph of code entities, dependencies, and "
    "relationships. Every edge is explained — no vector store needed.",
    author="OWNEX",
    icon="FileCode",
    capabilities=[
        Capability(
            domain="code_graph",
            name="Code Knowledge Graph",
            description="Build a queryable graph from any codebase",
        ),
        Capability(
            domain="dependency_analysis",
            name="Dependency Analysis",
            description="Map module dependencies, imports, and call graphs",
        ),
        Capability(
            domain="code_search",
            name="Semantic Code Search",
            description="Search code by intent, not just text matching",
        ),
    ],
    hooks={
        "codebase_analyze": "graphify.hooks.on_codebase_analyze",
        "code_context": "graphify.hooks.on_code_context",
    },
    providers=["graphify_code"],
    hot_reloadable=True,
    requires_core="5.0.0",
)
