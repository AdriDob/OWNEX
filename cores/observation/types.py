"""Observation types and data structures for the sensor network."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ObservationType(StrEnum):
    """Types of observations the sensor network can produce."""

    VULNERABILITY = "vulnerability"
    OPPORTUNITY = "opportunity"
    CHANGE = "change"
    THREAT = "threat"
    INTELLIGENCE = "intelligence"
    EVIDENCE = "evidence"
    ANOMALY = "anomaly"
    METRIC = "metric"


class SourceType(StrEnum):
    """Types of sources sensors can monitor."""

    INTERNET = "internet"
    PLATFORM = "platform"
    REPOSITORY = "repository"
    API = "api"
    LOCAL_FILE = "local_file"
    BROWSER = "browser"
    DOCUMENTATION = "documentation"
    INTERNAL = "internal"


class Severity(StrEnum):
    """Severity levels for observations."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(frozen=True)
class Evidence:
    """Immutable evidence attached to an observation."""

    source: str
    source_type: SourceType
    content: str | bytes
    evidence_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    hash: str = ""
    verified: bool = False

    def __post_init__(self):
        if not self.hash and isinstance(self.content, str):
            import hashlib

            object.__setattr__(self, "hash", hashlib.sha256(self.content.encode()).hexdigest()[:16])
        elif not self.hash and isinstance(self.content, bytes):
            import hashlib

            object.__setattr__(self, "hash", hashlib.sha256(self.content).hexdigest()[:16])


@dataclass
class Observation:
    """Core observation produced by sensors."""

    observation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    observation_type: ObservationType = ObservationType.INTELLIGENCE
    source: str = ""
    source_type: SourceType = SourceType.INTERNAL
    title: str = ""
    description: str = ""
    severity: Severity = Severity.INFO
    confidence: float = 0.0  # 0.0 - 1.0
    priority: float = 0.0  # Computed priority score
    evidence: list[Evidence] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)
    sensor_id: str = ""
    sensor_name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    raw_data: dict[str, Any] = field(default_factory=dict)

    # Deduplication
    fingerprint: str = ""  # Unique fingerprint for deduplication
    duplicates: list[str] = field(default_factory=list)  # Other observation IDs

    # Learning
    feedback_score: float | None = None  # -1.0 to 1.0 (negative = false positive)
    learning_weight: float = 1.0

    def add_evidence(self, evidence: Evidence) -> None:
        self.evidence.append(evidence)

    def compute_fingerprint(self) -> str:
        """Compute unique fingerprint for deduplication."""
        import hashlib

        key_parts = [
            self.observation_type.value,
            self.source,
            self.title.lower().strip(),
            str(sorted(self.tags)),
        ]
        fp = hashlib.sha256("|".join(key_parts).encode()).hexdigest()[:16]
        object.__setattr__(self, "fingerprint", fp)
        return fp


@dataclass
class SensorMetrics:
    """Runtime metrics for a sensor."""

    sensor_id: str
    total_observations: int = 0
    accepted_observations: int = 0
    rejected_observations: int = 0
    false_positives: int = 0
    true_positives: int = 0
    avg_confidence: float = 0.0
    avg_priority: float = 0.0
    last_run: str | None = None
    avg_duration_ms: float = 0.0
    error_count: int = 0
    resource_usage: dict[str, float] = field(default_factory=dict)

    @property
    def acceptance_rate(self) -> float:
        if self.total_observations == 0:
            return 0.0
        return self.accepted_observations / self.total_observations

    @property
    def precision(self) -> float:
        total = self.true_positives + self.false_positives
        if total == 0:
            return 0.0
        return self.true_positives / total

    @property
    def efficiency_score(self) -> float:
        """Composite score: acceptance_rate * precision / (1 + avg_duration)."""
        return self.acceptance_rate * self.precision / (1 + self.avg_duration_ms / 1000)


@dataclass
class SensorConfig:
    """Configuration for a sensor."""

    sensor_id: str
    name: str
    source_type: SourceType
    enabled: bool = True
    interval_seconds: int = 300  # 5 minutes default
    max_concurrent_runs: int = 1
    timeout_seconds: int = 60
    priority_weight: float = 1.0
    confidence_threshold: float = 0.3
    severity_threshold: Severity = Severity.LOW
    tags: set[str] = field(default_factory=set)
    config: dict[str, Any] = field(default_factory=dict)
    resource_limits: dict[str, float] = field(default_factory=dict)  # cpu%, memory_mb, network_mbps
    dependencies: list[str] = field(default_factory=list)  # Other sensor IDs this depends on


@dataclass
class SensorResult:
    """Result of a sensor execution."""

    sensor_id: str
    success: bool
    observations: list[Observation] = field(default_factory=list)
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
