from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.offensive.attack.models import ProbeRequest  # noqa: F401 — re-exported for compatibility


@dataclass
class ProbeResponse:
    """The HTTP response received by the probe."""

    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""
    body_size: int = 0
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "headers": dict(self.headers),
            "body": self.body[:2000],
            "body_size": self.body_size,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass
class ProbeEvidence:
    """Evidence collected from a probe test."""

    label: str  # "baseline", "test", "verify"
    request: ProbeRequest = field(default_factory=lambda: ProbeRequest("", ""))
    response: ProbeResponse = field(default_factory=lambda: ProbeResponse(status_code=0, body=""))
    findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "request": self.request.to_dict(),
            "response": self.response.to_dict(),
            "findings": self.findings,
        }


@dataclass
class ProbeResult:
    """Result of probing a hypothesis with real HTTP requests."""

    hypothesis_id: str
    vulnerability_type: str
    endpoint: str
    method: str

    confirmed: bool = False
    confidence: float = 0.0
    evidence: list[ProbeEvidence] = field(default_factory=list)

    # Confirmed vulnerability details
    test_value: str = ""
    vulnerable_param: str = ""
    test_request: ProbeRequest | None = None
    baseline_response: ProbeResponse | None = None
    test_response: ProbeResponse | None = None

    # Reasoning
    detection_method: str = ""  # "status_diff", "body_diff", "error_pattern", "timing", etc.
    detection_details: str = ""
    false_positive_risk: str = "unknown"  # "low", "medium", "high"
    alternative_explanations: list[str] = field(default_factory=list)

    # Metadata
    started_at: str = ""
    completed_at: str = ""
    error: str = ""

    @property
    def elapsed_seconds(self) -> float:
        if self.started_at and self.completed_at:
            try:
                start = datetime.fromisoformat(self.started_at)
                end = datetime.fromisoformat(self.completed_at)
                return (end - start).total_seconds()
            except (ValueError, TypeError):
                pass
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "vulnerability_type": self.vulnerability_type,
            "endpoint": self.endpoint,
            "method": self.method,
            "confirmed": self.confirmed,
            "confidence": round(self.confidence, 2),
            "evidence": [e.to_dict() for e in self.evidence],
            "test_value": self.test_value,
            "vulnerable_param": self.vulnerable_param,
            "detection_method": self.detection_method,
            "detection_details": self.detection_details,
            "false_positive_risk": self.false_positive_risk,
            "alternative_explanations": self.alternative_explanations,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "error": self.error,
        }
