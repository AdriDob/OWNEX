"""Observation model — the atomic unit of OWNEX v6.

An Observation is a raw signal from a Sensor before any classification.
It is NOT an opportunity — just evidence that something exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Observation:
    """A raw observation from the digital world.

    This is the atomic unit of OWNEX.
    Every Sensor emits Observations.
    Classification Engine decides if one is an opportunity.

    Idempotent by (sensor_id, external_id) — duplicate observations
    are collapsed by the ObservationCache.
    """

    # Identity
    id: str
    sensor_id: str
    external_id: str

    # Core content
    title: str
    description: str
    raw_data: dict[str, Any]

    # Origin
    source_type: str  # "bug_bounty", "dev_bounty", "ai_work", "freelance"
    source_name: str  # "hackerone", "github", "outlier", "algora"
    url: str | None = None

    # Reward signal (nullable — not all observations have it)
    estimated_reward_min: float = 0.0
    estimated_reward_max: float = 0.0

    # Effort estimation (hours — filled by NormalizationEngine)
    estimated_effort_hours: float = 0.0

    # Currency (filled by NormalizationEngine)
    reward_currency: str = "USD"
    reward_raw: str = ""

    # Classification hints
    tags: list[str] = field(default_factory=list)

    # Timing
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Confidence in the observation itself (not the signal quality)
    confidence: float = 1.0

    # Pipeline status (filled by engines)
    status: str = "new"  # new | normalized | identified | classified | opportunity | discarded

    # Fingerprint for identity resolution
    checksum: str = ""

    def dedup_key(self) -> str:
        """Unique key for deduplication."""
        return f"{self.sensor_id}:{self.external_id}"
