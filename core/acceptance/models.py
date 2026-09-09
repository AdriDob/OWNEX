"""Acceptance Intelligence — data models.

These are lightweight dataclasses for in-memory analysis.
Persistent storage uses the existing SubmissionRecord model
in database/models.py and PayoutRecord in models_economic.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AcceptanceOutcome:
    """The result of a single report submission."""

    report_id: int
    platform: str
    vulnerability_type: str
    severity: str
    status: str  # accepted, rejected, won, dismissed, pending
    payout: float = 0.0
    response_time_days: float = 0.0
    has_poc: bool = False
    has_evidence: bool = False
    description_length: int = 0
    repro_steps_count: int = 0
    cvss_score: float = 0.0
    cwe_id: str = ""
    submitted_at: datetime | None = None
    resolved_at: datetime | None = None
    notes: str = ""


@dataclass
class SubmissionRecord:
    """A record used for pattern analysis."""

    outcome: AcceptanceOutcome
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlatformProfile:
    """Learned acceptance patterns for a single platform."""

    platform: str
    total_submissions: int = 0
    accepted: int = 0
    rejected: int = 0
    pending: int = 0
    avg_payout: float = 0.0
    total_payout: float = 0.0
    avg_response_days: float = 0.0
    acceptance_rate: float = 0.0
    by_type: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_severity: dict[str, dict[str, Any]] = field(default_factory=dict)

    def update(self, outcome: AcceptanceOutcome) -> None:
        self.total_submissions += 1
        if outcome.status == "accepted" or outcome.status == "won":
            self.accepted += 1
            self.total_payout += outcome.payout
        elif outcome.status == "rejected" or outcome.status == "dismissed":
            self.rejected += 1
        else:
            self.pending += 1

        self.acceptance_rate = self.accepted / max(self.total_submissions - self.pending, 1)
        self.avg_payout = self.total_payout / max(self.accepted, 1)
        if outcome.response_time_days > 0:
            prev = self.avg_response_days * (self.total_submissions - 1)
            self.avg_response_days = (prev + outcome.response_time_days) / self.total_submissions

        vtype = outcome.vulnerability_type
        if vtype not in self.by_type:
            self.by_type[vtype] = {"total": 0, "accepted": 0, "rejected": 0, "rate": 0.0}
        self.by_type[vtype]["total"] += 1
        if outcome.status in ("accepted", "won"):
            self.by_type[vtype]["accepted"] += 1
        elif outcome.status in ("rejected", "dismissed"):
            self.by_type[vtype]["rejected"] += 1
        self.by_type[vtype]["rate"] = self.by_type[vtype]["accepted"] / max(self.by_type[vtype]["total"], 1)

        sev = outcome.severity
        if sev not in self.by_severity:
            self.by_severity[sev] = {"total": 0, "accepted": 0, "rejected": 0, "rate": 0.0}
        self.by_severity[sev]["total"] += 1
        if outcome.status in ("accepted", "won"):
            self.by_severity[sev]["accepted"] += 1
        elif outcome.status in ("rejected", "dismissed"):
            self.by_severity[sev]["rejected"] += 1
        self.by_severity[sev]["rate"] = self.by_severity[sev]["accepted"] / max(self.by_severity[sev]["total"], 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "total_submissions": self.total_submissions,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "pending": self.pending,
            "avg_payout": round(self.avg_payout, 2),
            "total_payout": round(self.total_payout, 2),
            "avg_response_days": round(self.avg_response_days, 1),
            "acceptance_rate": round(self.acceptance_rate, 3),
            "by_type": self.by_type,
            "by_severity": self.by_severity,
        }


@dataclass
class OptimizerSuggestion:
    """A concrete suggestion to improve a report."""

    field: str
    current: str
    suggestion: str
    reason: str
    impact: str  # high, medium, low
    expected_boost: float  # percentage points


@dataclass
class PredictionResult:
    """Acceptance probability prediction for a report."""

    probability: float
    confidence: str  # high, medium, low
    platform: str
    top_factors: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[OptimizerSuggestion] = field(default_factory=list)
