"""Triager Simulator — evaluates hypothesis quality, evidence completeness, and acceptance.

Simulates exactly how a human triager thinks:
  - Is it reproducible? Is it a dupe? Is it in scope?
  - Evidence completeness scoring (0-100)
  - Acceptance probability with specific objections
  - Questions a triager would ask
"""

from __future__ import annotations

import logging
from typing import Any

from core.offensive.models import (
    AcceptancePrediction,
    EvidenceCompleteness,
    EvidenceItem,
    Hypothesis,
)

logger = logging.getLogger("orion.core.offensive.triager")

EVIDENCE_CHECKS: list[dict[str, Any]] = [
    {"name": "Reproduction steps", "weight": 2.0, "check": lambda h: bool(h.test_instructions)},
    {"name": "Impact described", "weight": 2.0, "check": lambda h: bool(h.description)},
    {"name": "Why human would investigate", "weight": 1.5, "check": lambda h: bool(h.why_human_would_investigate)},
    {"name": "Alternative explanations", "weight": 1.5, "check": lambda h: bool(h.alternative_explanations)},
    {"name": "Scope verified", "weight": 1.5, "check": lambda h: bool(h.scope_check)},
    {"name": "Reproducibility notes", "weight": 1.5, "check": lambda h: bool(h.reproducibility_notes)},
    {"name": "Contradictions considered", "weight": 1.0, "check": lambda h: bool(h.contradictions)},
    {"name": "Multiple signals", "weight": 1.0, "check": lambda h: len(h.signals) >= 2},
    {
        "name": "Relationship context",
        "weight": 0.5,
        "check": lambda h: bool(h.relationship_context.siblings or h.relationship_context.parent_endpoint),
    },
    {
        "name": "Weakness identified (why triager might reject)",
        "weight": 1.5,
        "check": lambda h: bool(h.why_triager_might_reject),
    },
]


class TriagerSimulator:
    """Simulates human triage judgment on a hypothesis.

    Scores a hypothesis on the dimensions that matter most to
    platform triagers (HackerOne, Bugcrowd, Intigriti).

    The simulator scores evidence completeness (0-100) and
    predicts acceptance probability with specific reasoning.
    """

    def evaluate(self, hypothesis: Hypothesis) -> dict[str, Any]:
        """Run a hypothesis through complete triage simulation."""
        evidence = self._score_evidence(hypothesis)
        acceptance = self._predict_acceptance(hypothesis, evidence)

        return {
            "hypothesis_id": hypothesis.id,
            "evidence_completeness": {
                "score": round(evidence.score, 1),
                "items": [
                    {"name": i.name, "present": i.present, "weight": i.weight, "notes": i.notes} for i in evidence.items
                ],
                "gaps": evidence.gaps,
                "strong_points": evidence.strong_points,
                "passed": evidence.passed,
                "total": evidence.total,
            },
            "acceptance_prediction": {
                "probability": round(acceptance.probability, 2),
                "positive_signals": acceptance.positive_signals,
                "risk_factors": acceptance.risk_factors,
                "questions_triager_will_ask": acceptance.questions_triager_will_ask,
                "expected_verdict": acceptance.expected_verdict,
            },
            "verdict": self._final_verdict(evidence.score, acceptance.probability),
        }

    # ── Evidence Completeness (0-100) ─────────────────────────────

    def _score_evidence(self, hypothesis: Hypothesis) -> EvidenceCompleteness:
        items: list[EvidenceItem] = []
        for check in EVIDENCE_CHECKS:
            result = check["check"](hypothesis)
            items.append(
                EvidenceItem(
                    name=check["name"],
                    present=result,
                    weight=check["weight"],
                    notes="" if result else f"Missing: {check['name']}",
                )
            )

        max_weight = sum(i.weight for i in items)
        earned = sum(i.weight for i in items if i.present)
        score = (earned / max_weight * 100) if max_weight > 0 else 0.0

        gaps = [i.name for i in items if not i.present]
        strong_points = [i.name for i in items if i.present and i.weight >= 1.5]

        return EvidenceCompleteness(
            score=score,
            items=items,
            gaps=gaps,
            strong_points=strong_points,
        )

    # ── Acceptance Prediction ─────────────────────────────────────

    def _predict_acceptance(self, hypothesis: Hypothesis, evidence: EvidenceCompleteness) -> AcceptancePrediction:
        positive_signals: list[str] = []
        risk_factors: list[str] = []
        questions: list[str] = []

        # Evidence-based scoring
        evidence_factor = evidence.score / 100  # 0.0-1.0

        if evidence.score >= 70:
            positive_signals.append("Strong evidence completeness (>70%)")
        else:
            risk_factors.append(f"Evidence completeness only {evidence.score:.0f}%")

        # Confidence-based scoring
        if hypothesis.confidence >= 0.7:
            positive_signals.append(f"High reasoner confidence ({hypothesis.confidence:.2f})")
        elif hypothesis.confidence >= 0.5:
            pass  # Moderate — neither positive nor risk
        else:
            risk_factors.append(f"Low reasoner confidence ({hypothesis.confidence:.2f})")

        # Severity-based scoring
        if hypothesis.severity in ("high", "critical"):
            positive_signals.append(f"Severity: {hypothesis.severity}")
        elif hypothesis.severity == "low":
            risk_factors.append("Low severity — may be deprioritized")

        # Contradiction check
        if hypothesis.contradictions:
            unresolved = sum(1 for c in hypothesis.contradictions if c.confidence_reduction > 0.2)
            if unresolved > 0:
                risk_factors.append(f"{unresolved} high-impact contradictions not ruled out")
        else:
            risk_factors.append("No contradictions considered — triager will find them")

        # Contradiction-adjusted confidence
        adj_confidence = hypothesis.confidence
        for c in hypothesis.contradictions:
            adj_confidence -= c.confidence_reduction * hypothesis.confidence
        adj_confidence = max(0.0, adj_confidence)

        # Final probability
        probability = (
            (evidence_factor * 0.5)
            + (adj_confidence * 0.3)
            + (0.2 if hypothesis.severity in ("high", "critical") else 0.1)
        )
        probability = min(max(probability, 0.05), 0.98)

        # Triager questions
        if not hypothesis.reproducibility_notes:
            questions.append("Can you provide detailed reproduction steps with two accounts?")
        if hypothesis.severity == "low":
            questions.append("What is the actual business impact? Low severity may not warrant investigation.")
        if not hypothesis.scope_check:
            questions.append("Is this endpoint confirmed in scope for the program?")
        if evidence.score < 50:
            questions.append("The evidence is weak — can you strengthen the PoC?")
        if hypothesis.contradictions:
            for c in hypothesis.contradictions[:2]:
                questions.append(f"Have you ruled out: {c.label}?")

        verdict = self._final_verdict(evidence.score, probability)

        return AcceptancePrediction(
            probability=probability,
            positive_signals=positive_signals,
            risk_factors=risk_factors,
            questions_triager_will_ask=questions,
            expected_verdict=verdict,
        )

    @staticmethod
    def _final_verdict(evidence_score: float, acceptance_probability: float) -> str:
        combined = (evidence_score / 100 * 0.4) + (acceptance_probability * 0.6)
        if combined >= 0.8:
            return "report_ready"
        if combined >= 0.55:
            return "needs_improvement"
        if combined >= 0.3:
            return "needs_review"
        return "insufficient"
