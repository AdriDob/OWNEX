"""AcceptancePredictor — estimates report acceptance probability.

Evaluates findings against known acceptance factors and returns a
structured prediction with actionable feedback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cores.predictor.scoring import ScoreWeights, compute_acceptance_score

ACCEPTANCE_THRESHOLD = 0.65


@dataclass
class PredictionResult:
    acceptance_probability: float
    duplicate_risk: float
    confidence_score: float
    missing_evidence: list[str]
    missing_validation: list[str]
    suggested_next_steps: list[str]
    ready_for_submission: bool
    factors: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class AcceptancePredictor:
    def __init__(self, weights: ScoreWeights | None = None) -> None:
        self._weights = weights or ScoreWeights()

    def predict(self, finding: dict[str, Any]) -> PredictionResult:
        factors = self._evaluate_factors(finding)
        score = compute_acceptance_score(**factors, weights=self._weights)
        duplicate_risk = factors.get("duplicate_risk", 0.0)
        missing = self._find_missing_evidence(finding)
        missing_val = self._find_missing_validation(finding)
        warnings_list: list[str] = []

        if missing:
            warnings_list.append("Incomplete evidence — reduce acceptance odds")
        if missing_val:
            warnings_list.append("Missing validation steps — high rejection risk")
        if duplicate_risk > 0.5:
            warnings_list.append("High duplicate risk — verify uniqueness")
        if factors.get("scope_compliance", 1.0) < 0.5:
            warnings_list.append("Out-of-scope finding — likely rejected")
        if factors.get("severity_justification", 1.0) < 0.4:
            warnings_list.append("Weak severity justification — improve rationale")

        next_steps = self._suggest_next_steps(missing, missing_val, duplicate_risk, score)

        return PredictionResult(
            acceptance_probability=round(score, 4),
            duplicate_risk=round(duplicate_risk, 4),
            confidence_score=round(self._compute_confidence(factors), 4),
            missing_evidence=missing,
            missing_validation=missing_val,
            suggested_next_steps=next_steps,
            ready_for_submission=score >= ACCEPTANCE_THRESHOLD,
            factors=factors,
            warnings=warnings_list,
        )

    def predict_many(self, findings: list[dict[str, Any]]) -> list[PredictionResult]:
        return [self.predict(f) for f in findings]

    def _evaluate_factors(self, finding: dict[str, Any]) -> dict[str, float]:
        severity_map = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.3, "info": 0.1}
        sev = finding.get("severity", "low")
        severity_score = severity_map.get(sev, 0.2)

        proof = finding.get("proof", {}) or {}

        return {
            "technical_confidence": 1.0 if len(proof.get("technical_detail", "") or "") > 200 else 0.0,
            "reproducibility": 1.0 if len(proof.get("reproduction_steps", "") or "") > 100 else 0.0,
            "evidence_completeness": self._rate_evidence(proof),
            "business_impact": min(1.0, finding.get("business_impact_score", 0.0)),
            "security_impact": severity_score,
            "scope_compliance": 1.0 if finding.get("in_scope", True) else 0.0,
            "duplicate_risk": min(1.0, finding.get("duplicate_probability", 0.0)),
            "report_quality": min(1.0, finding.get("quality_score", 0.5)),
            "severity_justification": self._rate_severity_justification(finding),
        }

    def _rate_evidence(self, proof: dict[str, Any]) -> float:
        parts = 0
        if proof.get("screenshots"):
            parts += 1
        if proof.get("request_response"):
            parts += 1
        if proof.get("logs"):
            parts += 1
        if proof.get("code"):
            parts += 1
        return min(1.0, parts / 4)

    def _rate_severity_justification(self, finding: dict[str, Any]) -> float:
        justification = finding.get("severity_justification", "") or ""
        if len(justification) > 300:
            return 1.0
        if len(justification) > 100:
            return 0.5
        return 0.2

    def _compute_confidence(self, factors: dict[str, float]) -> float:
        return sum(factors.values()) / max(len(factors), 1)

    def _find_missing_evidence(self, finding: dict[str, Any]) -> list[str]:
        proof = finding.get("proof", {}) or {}
        missing: list[str] = []
        if not proof.get("screenshots"):
            missing.append("Screenshots of the vulnerability")
        if not proof.get("request_response"):
            missing.append("HTTP request/response pairs")
        if not proof.get("logs"):
            missing.append("Server or application logs")
        if not proof.get("code"):
            missing.append("Exploit code or PoC")
        return missing

    def _find_missing_validation(self, finding: dict[str, Any]) -> list[str]:
        steps = []
        if not finding.get("reproduced", False):
            steps.append("Confirm reproduction in clean environment")
        if not finding.get("verified_scope", False):
            steps.append("Verify target is in scope")
        return steps

    def _suggest_next_steps(
        self,
        missing_evidence: list[str],
        missing_validation: list[str],
        duplicate_risk: float,
        score: float,
    ) -> list[str]:
        steps: list[str] = []
        steps.extend(f"Add: {e}" for e in missing_evidence)
        steps.extend(f"Complete: {v}" for v in missing_validation)
        if duplicate_risk > 0.3 and duplicate_risk <= 0.7:
            steps.append("Search for similar reported issues")
        if duplicate_risk > 0.7:
            steps.append("Consider pivoting to a different attack vector")
        if score < ACCEPTANCE_THRESHOLD:
            steps.append("Improve report quality before submission")
        steps.append("Final review by second researcher")
        return steps
