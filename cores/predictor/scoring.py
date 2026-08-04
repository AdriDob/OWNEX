"""Scoring weights and helpers for acceptance prediction."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreWeights:
    technical_confidence: float = 0.15
    reproducibility: float = 0.15
    evidence_completeness: float = 0.12
    business_impact: float = 0.12
    security_impact: float = 0.12
    scope_compliance: float = 0.10
    duplicate_risk: float = 0.08
    report_quality: float = 0.08
    severity_justification: float = 0.08

    @property
    def total(self) -> float:
        return sum(
            [
                self.technical_confidence,
                self.reproducibility,
                self.evidence_completeness,
                self.business_impact,
                self.security_impact,
                self.scope_compliance,
                self.duplicate_risk,
                self.report_quality,
                self.severity_justification,
            ]
        )


DEFAULT_WEIGHTS = ScoreWeights()


def compute_acceptance_score(
    technical_confidence: float,
    reproducibility: float,
    evidence_completeness: float,
    business_impact: float,
    security_impact: float,
    scope_compliance: float,
    duplicate_risk: float,
    report_quality: float,
    severity_justification: float,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> float:
    raw = (
        technical_confidence * weights.technical_confidence
        + reproducibility * weights.reproducibility
        + evidence_completeness * weights.evidence_completeness
        + business_impact * weights.business_impact
        + security_impact * weights.security_impact
        + scope_compliance * weights.scope_compliance
        + (1.0 - duplicate_risk) * weights.duplicate_risk
        + report_quality * weights.report_quality
        + severity_justification * weights.severity_justification
    )
    return max(0.0, min(1.0, raw))
