from dataclasses import dataclass, field
from typing import Any, Literal

from cores.validation.confidence import ConfidenceScore
from cores.validation.rules import ValidationReport


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
    def admit(self, verdict: Verdict) -> bool:
        return verdict.status == "confirmed" and verdict.confidence >= 0.6

    def reject_reason(self, verdict: Verdict) -> str:
        if verdict.status == "confirmed":
            return "Verdict is confirmed — no rejection reason."
        if verdict.status == "rejected":
            reasons = ["status=rejected", f"confidence={verdict.confidence:.2f}"]
            if verdict.validation.failed_rules:
                reasons.append(f"failed_rules={verdict.validation.failed_rules}")
            return " | ".join(reasons)
        if verdict.status == "inconclusive":
            return (
                f"status=inconclusive | confidence={verdict.confidence:.2f} "
                f"(below 0.6 threshold) | reproducibility={verdict.reproducibility_score:.2f}"
            )
        return f"status={verdict.status} (unexpected)"
