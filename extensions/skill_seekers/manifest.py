from __future__ import annotations

from core.extension.capabilities import Capability
from core.extension.manifest import ExtensionManifest

manifest = ExtensionManifest(
    id="skill_seekers",
    name="Skill Seekers",
    version="1.0.0",
    description="Convert documentation websites, GitHub repositories, and PDFs "
    "into AI skills with automatic conflict detection. Enables OWNEX "
    "to continuously grow its knowledge by ingesting external docs "
    "as agent-consumable skills.",
    author="OWNEX",
    icon="BookOpen",
    capabilities=[
        Capability(
            domain="skill_extraction",
            name="Skill Extraction",
            description="Extract AI skills from documentation and code repos",
        ),
        Capability(
            domain="conflict_detection",
            name="Conflict Detection",
            description="Auto-detect conflicting instructions across skills",
        ),
        Capability(
            domain="doc_ingestion",
            name="Documentation Ingestion",
            description="Ingest multi-source documentation into the skill library",
        ),
    ],
    hooks={
        "skill_learn": "skill_seekers.hooks.on_skill_learn",
        "doc_ingest": "skill_seekers.hooks.on_doc_ingest",
    },
    providers=["skill_seekers"],
    hot_reloadable=True,
    requires_core="5.0.0",
)
