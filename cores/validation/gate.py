from dataclasses import dataclass, field
from typing import Any, Literal

from cores.validation.confidence import ConfidenceScore
from cores.validation.rules import ValidationReport

DEFAULT_CONFIDENCE_THRESHOLD = 0.60

VULN_THRESHOLDS: dict[str, float] = {
    "idor": 0.85,
    "ssrf": 0.90,
    "xss": 0.80,
    "sqli": 0.80,
    "auth_bypass": 0.95,
    "rce": 0.90,
    "lfi": 0.85,
    "open_redirect": 0.80,
    "csrf": 0.75,
    "information_disclosure": 0.70,
    "directory_listing": 0.70,
    "unknown": DEFAULT_CONFIDENCE_THRESHOLD,
}


@dataclass
class Verdict:
    hot_path_id: str
    status: Literal["confirmed", "rejected", "inconclusive"]
    confidence: float
    reproducibility_score: float
    validation: ValidationReport
    confidence_details: ConfidenceScore
    evidence_links: list[str]
    reason: str
    retry_count: int
    timestamp: str
    vulnerability_type: str = "unknown"
    alternative_explanations: list[dict[str, Any]] = field(default_factory=list)
    missing_verifications: list[str] = field(default_factory=list)
    next_best_test: dict[str, Any] | None = None
    uncertainty_level: str = "unknown"


class ReportGate:
    def __init__(self) -> None:
        self._thresholds: dict[str, float] = dict(VULN_THRESHOLDS)

    def get_threshold(self, vuln_type: str) -> float:
        return self._thresholds.get(vuln_type.lower(), DEFAULT_CONFIDENCE_THRESHOLD)

    def set_threshold(self, vuln_type: str, threshold: float) -> None:
        self._thresholds[vuln_type.lower()] = max(0.0, min(1.0, threshold))

    def get_thresholds(self) -> dict[str, float]:
        return dict(self._thresholds)

    def reset_thresholds(self) -> None:
        self._thresholds = dict(VULN_THRESHOLDS)

    def admit(self, verdict: Verdict) -> bool:
        threshold = self.get_threshold(verdict.vulnerability_type)
        return verdict.status == "confirmed" and verdict.confidence >= threshold

    def reject_reason(self, verdict: Verdict) -> str:
        threshold = self.get_threshold(verdict.vulnerability_type)
        if verdict.status == "confirmed":
            if verdict.confidence >= threshold:
                return f"Verdict is confirmed — confidence {verdict.confidence:.2f} >= {verdict.vulnerability_type} threshold {threshold:.2f}."
            return (
                f"Confirmed but below {verdict.vulnerability_type} threshold: "
                f"confidence {verdict.confidence:.2f} < {threshold:.2f}"
            )
        if verdict.status == "rejected":
            reasons = ["status=rejected", f"confidence={verdict.confidence:.2f}", f"threshold={threshold:.2f}"]
            if verdict.validation.failed_rules:
                reasons.append(f"failed_rules={verdict.validation.failed_rules}")
            return " | ".join(reasons)
        if verdict.status == "inconclusive":
            return (
                f"status=inconclusive | confidence={verdict.confidence:.2f} "
                f"(below {verdict.vulnerability_type} threshold {threshold:.2f}) | "
                f"reproducibility={verdict.reproducibility_score:.2f}"
            )
        return f"status={verdict.status} (unexpected)"
