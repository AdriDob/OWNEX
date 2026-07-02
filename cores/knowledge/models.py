from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class KnowledgeContentType(str, Enum):
    advisory = "advisory"
    template = "template"
    rule = "rule"
    report = "report"
    research = "research"
    payload = "payload"
    checklist = "checklist"
    reference = "reference"
    other = "other"


@dataclass
class KnowledgeMetadata:
    source: str
    source_id: str
    source_type: str
    source_url: str | None = None
    published_at: str | None = None
    version: str | None = None
    tags: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    cwe_ids: list[str] = field(default_factory=list)
    cve_ids: list[str] = field(default_factory=list)
    severity: str | None = None
    confidence: float = 0.0
    references: list[str] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False)


@dataclass
class RawKnowledgeDocument:
    source_name: str
    external_id: str
    raw_content: dict[str, Any]
    payload_type: KnowledgeContentType = KnowledgeContentType.other
    ingest_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: KnowledgeMetadata = field(default_factory=lambda: KnowledgeMetadata(source="unknown", source_id="unknown", source_type="unknown"))


@dataclass
class CanonicalKnowledgeArtifact:
    artifact_id: str
    title: str
    summary: str | None
    description: str | None
    content_type: KnowledgeContentType
    body: str | None
    canonical_entities: list[str] = field(default_factory=list)
    metadata: KnowledgeMetadata = field(default_factory=lambda: KnowledgeMetadata(source="unknown", source_id="unknown", source_type="unknown"))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: int = 1
    fingerprint: str | None = None
    dedup_source_ids: list[str] = field(default_factory=list)

    def bump_version(self) -> None:
        self.version += 1
        self.updated_at = datetime.utcnow().isoformat()


@dataclass
class KnowledgeEntity:
    entity_id: str
    name: str
    category: str
    description: str | None = None
    cwe_ids: list[str] = field(default_factory=list)
    cve_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    confidence: float = 0.0
    severity: str | None = None
    references: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class KnowledgeRelationship:
    relation_id: str
    source_artifact_id: str
    target_artifact_id: str
    relation_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
