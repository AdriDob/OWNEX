from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from cores.contracts.base import Artifact


@dataclass
class KnowledgeSourceInfo:
    name: str
    source_type: str
    provider: str
    homepage: str | None = None
    description: str | None = None
    version: str | None = None
    metadata: dict[str, Any] | None = None


class KnowledgeSourceConnector(ABC):
    """Abstract connector that imports raw knowledge payloads from a source."""

    name: str = "base"
    provider: str = "generic"
    source_type: str = "knowledge"

    @abstractmethod
    def discover(self) -> list[dict[str, Any]]:
        """Discover available raw payloads for ingestion."""

    @abstractmethod
    def fetch(self, identifier: str) -> dict[str, Any]:
        """Fetch a single raw payload by identifier."""

    @abstractmethod
    def info(self) -> KnowledgeSourceInfo:
        """Return metadata about the source connector."""


class KnowledgeParser(ABC):
    @abstractmethod
    def parse(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        """Parse raw source content into a structured intermediate representation."""


class KnowledgeNormalizer(ABC):
    @abstractmethod
    def normalize(self, parsed_payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize parsed content into canonical knowledge fields."""


class KnowledgeDeduplicator(ABC):
    @abstractmethod
    def fingerprint(self, normalized_record: dict[str, Any]) -> str:
        """Compute a stable fingerprint for deduplication."""

    @abstractmethod
    def merge(self, existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        """Merge two matching records into a stronger canonical view."""


class KnowledgeEnricher(ABC):
    @abstractmethod
    def enrich(self, normalized_record: dict[str, Any]) -> dict[str, Any]:
        """Enrich a canonical knowledge record with additional signals."""


class KnowledgeIndexer(ABC):
    @abstractmethod
    def index(self, normalized_record: dict[str, Any]) -> None:
        """Index a knowledge artifact for search and retrieval."""

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search indexed knowledge artifacts."""


class KnowledgeGraphService(ABC):
    @abstractmethod
    def add_relation(self, source_id: str, target_id: str, relation_type: str, metadata: dict[str, Any] | None = None) -> None:
        """Register a semantic relation between two knowledge artifacts."""

    @abstractmethod
    def get_relations(self, artifact_id: str) -> list[dict[str, Any]]:
        """Return relations for a given artifact."""

    @abstractmethod
    def infer_related_entities(self, artifact_id: str) -> list[str]:
        """Infer related entity identifiers from knowledge graph context."""


class KnowledgeStore(ABC):
    @abstractmethod
    def save_source(self, source: KnowledgeSourceInfo) -> str:
        """Persist source metadata and return an internal source id."""

    @abstractmethod
    def save_artifact(self, artifact: dict[str, Any]) -> str:
        """Persist a canonical knowledge artifact and return its id."""

    @abstractmethod
    def save_relationship(self, relation: dict[str, Any]) -> str:
        """Persist a semantic relation and return its id."""

    @abstractmethod
    def find_artifacts(self, fingerprint: str) -> list[dict[str, Any]]:
        """Locate existing artifacts by deduplication fingerprint."""

    @abstractmethod
    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        """Retrieve a persisted artifact."""


class KnowledgePipeline(ABC):
    @abstractmethod
    def run(self, payloads: Iterable[dict[str, Any]]) -> list[str]:
        """Execute the ingestion pipeline and return persisted artifact ids."""


@dataclass
class KnowledgePipelineStage(Artifact):
    name: str = "unnamed"
    description: str = ""
    status: str = "pending"
    duration_seconds: float = 0.0
    details: dict[str, Any] | None = None

    def complete(self, duration_seconds: float, details: dict[str, Any] | None = None) -> None:
        self.status = "completed"
        self.duration_seconds = duration_seconds
        self.details = details or {}


@dataclass
class KnowledgePipelineReport(Artifact):
    stages: list[KnowledgePipelineStage] | None = None
    artifact_ids: list[str] | None = None
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.stages = self.stages or []
        self.artifact_ids = self.artifact_ids or []
        self.errors = self.errors or []
