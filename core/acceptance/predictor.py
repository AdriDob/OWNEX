"""Acceptance Intelligence — acceptance probability predictor.

Estimates the likelihood that a report will be accepted
based on historical patterns and report characteristics.
"""

from __future__ import annotations

import logging
from typing import Any

from core.acceptance.analyzer import AcceptanceAnalyzer
from core.acceptance.models import OptimizerSuggestion, PredictionResult

logger = logging.getLogger("orion.core.acceptance.predictor")


class AcceptancePredictor:
    """Predicts acceptance probability for reports based on historical data."""

    def __init__(self, analyzer: AcceptanceAnalyzer | None = None) -> None:
        self._analyzer = analyzer or AcceptanceAnalyzer()

    @property
    def analyzer(self) -> AcceptanceAnalyzer:
        return self._analyzer

    def predict(
        self,
        report: dict[str, Any],
        platform: str = "hackerone",
    ) -> PredictionResult:
        """Predict acceptance probability for a report.

        Args:
            report: Report data with keys like vulnerability_type, severity,
                    has_poc, has_evidence, description_length, etc.
            platform: Target platform.

        Returns:
            PredictionResult with probability, confidence, top factors, suggestions.
        """
        platform_lower = (
            platform.lower().replace("h1", "hackerone").replace("bc", "bugcrowd").replace("inti", "intigriti")
        )

        profile = self._analyzer.get_profile(platform_lower)
        factors: list[dict[str, Any]] = []
        base_probability = 0.5  # Start at 50% (no information)

        # Factor 1: Platform base acceptance rate
        if profile and profile.total_submissions > 0:
            base_probability = profile.acceptance_rate
            factors.append(
                {
                    "name": "platform_base_rate",
                    "value": round(profile.acceptance_rate, 3),
                    "weight": 0.3,
                    "detail": f"{platform} base acceptance rate: {profile.acceptance_rate:.0%}",
                }
            )

        # Factor 2: Vulnerability type acceptance rate
        vuln_type = (report.get("vulnerability_type") or "").lower()
        type_rate = None
        if profile and vuln_type in profile.by_type:
            type_stats = profile.by_type[vuln_type]
            if type_stats["total"] >= 3:
                type_rate = type_stats["rate"]
                factors.append(
                    {
                        "name": "vuln_type_rate",
                        "value": round(type_rate, 3),
                        "weight": 0.2,
                        "detail": f"{vuln_type} acceptance rate: {type_rate:.0%} ({type_stats['accepted']}/{type_stats['total']})",
                    }
                )

        # Factor 3: Severity acceptance rate
        severity = (report.get("severity") or "").lower()
        sev_rate = None
        if profile and severity in profile.by_severity:
            sev_stats = profile.by_severity[severity]
            if sev_stats["total"] >= 3:
                sev_rate = sev_stats["rate"]
                factors.append(
                    {
                        "name": "severity_rate",
                        "value": round(sev_rate, 3),
                        "weight": 0.15,
                        "detail": f"{severity} acceptance rate: {sev_rate:.0%} ({sev_stats['accepted']}/{sev_stats['total']})",
                    }
                )

        # Factor 4: Evidence completeness
        has_poc = bool(report.get("poc")) or bool(report.get("python_script"))
        has_evidence = bool(report.get("evidence"))
        has_reproduction = bool(report.get("reproduction_steps"))
        completeness = sum([has_poc, has_evidence, has_reproduction]) / 3.0
        factors.append(
            {
                "name": "evidence_completeness",
                "value": round(completeness, 2),
                "weight": 0.15,
                "detail": f"Evidence completeness: {completeness:.0%}",
            }
        )

        # Factor 5: Description quality
        desc = report.get("description") or ""
        desc_quality = min(len(desc) / 200, 1.0)
        factors.append(
            {
                "name": "description_quality",
                "value": round(desc_quality, 2),
                "weight": 0.1,
                "detail": f"Description: {len(desc)} chars (target: 200+)",
            }
        )

        # Factor 6: CVSS score
        cvss = float(report.get("cvss_score", 0) or 0)
        cvss_factor = min(cvss / 10.0, 1.0)
        factors.append(
            {
                "name": "cvss_strength",
                "value": round(cvss_factor, 2),
                "weight": 0.1,
                "detail": f"CVSS: {cvss}/10",
            }
        )

        # Calculate weighted probability
        total_weight = sum(f["weight"] for f in factors)
        weighted_sum = base_probability * 0.3  # Initialize with base

        for f in factors:
            if f["name"] != "platform_base_rate":
                weighted_sum += f["value"] * f["weight"]
            else:
                weighted_sum += f["value"] * 0.3  # Already counted in init

        probability = weighted_sum / max(total_weight, 0.01)
        probability = max(0.05, min(0.98, probability))

        # Confidence level
        sample_count = profile.total_submissions if profile else 0
        if sample_count >= 30:
            confidence = "high"
        elif sample_count >= 10:
            confidence = "medium"
        else:
            confidence = "low"

        # Generate suggestions for improvement
        suggestions = self._generate_suggestions(report, platform_lower, probability)

        return PredictionResult(
            probability=round(probability, 3),
            confidence=confidence,
            platform=platform_lower,
            top_factors=factors,
            suggestions=suggestions,
        )

    def _generate_suggestions(
        self,
        report: dict[str, Any],
        platform: str,
        current_prob: float,
    ) -> list[OptimizerSuggestion]:
        suggestions = []

        desc = report.get("description", "") or ""
        if len(desc) < 100:
            suggestions.append(
                OptimizerSuggestion(
                    field="description",
                    current=f"{len(desc)} chars",
                    suggestion="Expand the description to at least 200 characters with technical details",
                    reason="Reports with detailed descriptions have significantly higher acceptance rates",
                    impact="high",
                    expected_boost=0.15,
                )
            )

        poc = report.get("poc")
        if not poc:
            suggestions.append(
                OptimizerSuggestion(
                    field="poc",
                    current="No PoC",
                    suggestion="Include a curl command as proof of concept",
                    reason="Triagers consistently prioritize reports with working PoCs",
                    impact="high",
                    expected_boost=0.20,
                )
            )

        evidence = report.get("evidence", [])
        if not evidence:
            suggestions.append(
                OptimizerSuggestion(
                    field="evidence",
                    current="No evidence",
                    suggestion="Attach screenshots, HAR files, or request/response pairs",
                    reason="Evidence dramatically increases reproducibility and credibility",
                    impact="high",
                    expected_boost=0.15,
                )
            )

        steps = report.get("reproduction_steps", [])
        if not steps:
            suggestions.append(
                OptimizerSuggestion(
                    field="reproduction_steps",
                    current="No reproduction steps",
                    suggestion="Add clear, numbered steps to reproduce the vulnerability",
                    reason="Triagers need to verify the issue quickly and consistently",
                    impact="high",
                    expected_boost=0.15,
                )
            )

        vuln_type = report.get("vulnerability_type", "") or ""
        if not vuln_type:
            suggestions.append(
                OptimizerSuggestion(
                    field="vulnerability_type",
                    current="Not specified",
                    suggestion="Specify the vulnerability type (IDOR, SSRF, XSS, SQLi, etc.)",
                    reason="Clear classification helps triagers route the report correctly",
                    impact="medium",
                    expected_boost=0.10,
                )
            )

        severity = report.get("severity", "") or ""
        if not severity:
            suggestions.append(
                OptimizerSuggestion(
                    field="severity",
                    current="Not specified",
                    suggestion="Assign a severity level (critical/high/medium/low)",
                    reason="Helps triagers prioritize and assess impact",
                    impact="medium",
                    expected_boost=0.08,
                )
            )

        cvss = float(report.get("cvss_score", 0) or 0)
        if cvss <= 0:
            suggestions.append(
                OptimizerSuggestion(
                    field="cvss_score",
                    current="Not scored",
                    suggestion="Calculate and include a CVSS v3.1 score",
                    reason="Demonstrates professional assessment methodology",
                    impact="medium",
                    expected_boost=0.08,
                )
            )

        cwe = report.get("cwe_id", "") or report.get("cwe", "")
        if not cwe:
            suggestions.append(
                OptimizerSuggestion(
                    field="cwe_id",
                    current="Not specified",
                    suggestion="Include the relevant CWE identifier",
                    reason="Standard classification helps with automated triage systems",
                    impact="low",
                    expected_boost=0.05,
                )
            )

        return suggestions
