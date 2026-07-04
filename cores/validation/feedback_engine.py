"""FeedbackEngine — simulates triager review and returns actionable report feedback.

Connects AcceptancePredictor → validation rules → evidence builder into a
single "will this get accepted?" pipeline with specific improvement steps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cores.predictor.acceptance import ACCEPTANCE_THRESHOLD, AcceptancePredictor, PredictionResult
from cores.predictor.scoring import ScoreWeights


@dataclass
class ReportFeedback:
    acceptance_probability: float
    duplicate_risk: float
    ready_for_submission: bool
    triager_perspective: str
    missing_evidence: list[str]
    missing_validation: list[str]
    severity_concerns: list[str]
    reproducibility_concerns: list[str]
    scope_concerns: list[str]
    impact_concerns: list[str]
    suggested_fixes: list[str]
    priority_fixes: list[str]


class FeedbackEngine:
    def __init__(self, weights: ScoreWeights | None = None) -> None:
        self._predictor = AcceptancePredictor(weights)

    def analyze(self, finding: dict[str, Any]) -> ReportFeedback:
        prediction = self._predictor.predict(finding)
        concerns = self._extract_concerns(finding, prediction)
        fixes = self._generate_fixes(prediction, concerns)

        triager_note = self._simulate_triager(prediction, concerns)

        return ReportFeedback(
            acceptance_probability=prediction.acceptance_probability,
            duplicate_risk=prediction.duplicate_risk,
            ready_for_submission=prediction.ready_for_submission,
            triager_perspective=triager_note,
            missing_evidence=prediction.missing_evidence,
            missing_validation=prediction.missing_validation,
            severity_concerns=concerns["severity"],
            reproducibility_concerns=concerns["reproducibility"],
            scope_concerns=concerns["scope"],
            impact_concerns=concerns["impact"],
            suggested_fixes=fixes,
            priority_fixes=self._prioritize_fixes(prediction, fixes),
        )

    def _extract_concerns(
        self,
        finding: dict[str, Any],
        prediction: PredictionResult,
    ) -> dict[str, list[str]]:
        concerns: dict[str, list[str]] = {
            "severity": [],
            "reproducibility": [],
            "scope": [],
            "impact": [],
        }

        if prediction.factors.get("severity_justification", 1.0) < 0.5:
            concerns["severity"].append("Severity not well justified — triager may downgrade")
        if prediction.factors.get("security_impact", 0.0) < 0.3:
            concerns["severity"].append("Low security impact — may be marked as informational")

        steps = finding.get("proof", {}).get("reproduction_steps", "")
        if not steps or len(steps) < 50:
            concerns["reproducibility"].append("Reproduction steps too short or missing")
        if not finding.get("reproduced", False):
            concerns["reproducibility"].append("Not reproduced in clean environment")

        if not finding.get("in_scope", True):
            concerns["scope"].append("Target appears out of scope")
        if prediction.factors.get("scope_compliance", 1.0) < 0.5:
            concerns["scope"].append("Scope compliance is unclear")

        impact = finding.get("business_impact", "") or ""
        if len(impact) < 100:
            concerns["impact"].append("Business impact not clearly articulated")
        if prediction.factors.get("business_impact", 0.0) < 0.3:
            concerns["impact"].append("Business impact score is low")

        return concerns

    def _generate_fixes(
        self,
        prediction: PredictionResult,
        concerns: dict[str, list[str]],
    ) -> list[str]:
        fixes: list[str] = []

        if concerns["impact"]:
            fixes.append("Add a concrete business impact scenario (e.g., 'attacker could download all user PII')")
        if concerns["severity"]:
            fixes.append("Strengthen severity justification with CVSS vector or comparable CVEs")
        if concerns["reproducibility"]:
            fixes.append("Simplify reproduction to ≤3 curl commands")
            fixes.append("Record a short video or screenshot sequence")
        if concerns["scope"]:
            fixes.append("Explicitly state why the target is in scope (cite program policy)")

        if prediction.missing_evidence:
            fixes.append(f"Add missing evidence: {', '.join(prediction.missing_evidence[:3])}")
        if prediction.missing_validation:
            fixes.append(f"Complete validation: {', '.join(prediction.missing_validation[:2])}")
        if prediction.duplicate_risk > 0.5:
            fixes.append("Search program for similar reports before submitting")

        return fixes

    def _prioritize_fixes(
        self,
        prediction: PredictionResult,
        fixes: list[str],
    ) -> list[str]:
        urgent: list[str] = []
        if not prediction.ready_for_submission:
            urgent.append("IMPROVE: Report quality below threshold — do not submit as-is")
        if prediction.duplicate_risk > 0.7:
            urgent.append("BLOCKER: Very high duplicate risk — verify uniqueness first")
        if prediction.factors.get("scope_compliance", 1.0) < 0.3:
            urgent.append("BLOCKER: Probable out-of-scope finding — verify before proceeding")

        urgent.extend(fixes[:3])
        return urgent

    def _simulate_triager(
        self,
        prediction: PredictionResult,
        concerns: dict[str, list[str]],
    ) -> str:
        parts: list[str] = []

        if prediction.acceptance_probability >= 0.8:
            parts.append("This report looks solid. A triager would likely accept it quickly.")
        elif prediction.acceptance_probability >= ACCEPTANCE_THRESHOLD:
            parts.append("Acceptable report, but a triager would flag the following issues:")
        else:
            parts.append("A triager would likely reject or mark as needs-more-info:")

        for _category, items in concerns.items():
            for item in items:
                parts.append(f"  - {item}")

        if prediction.duplicate_risk > 0.5:
            parts.append("  - HIGH DUPLICATE PROBABILITY — triagers check for this first")

        parts.append(f"Estimated acceptance: {prediction.acceptance_probability:.0%}")
        return "\n".join(parts)
