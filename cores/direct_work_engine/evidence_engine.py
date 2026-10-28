"""Universal Evidence Engine — OWNEX 100/100.

Extends the existing Evidence Gate (P5) to ALL economic categories.
This is the routing layer — the actual evidence evaluation logic lives in:
- cores.direct_work_engine.reward_probability (EvidenceGate for bug bounty)
- cores.direct_work_engine.evidence_engine (NEW: category-specific evaluators)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.direct_work_engine.reward_probability import (
    EvidenceGate,
    get_evidence_gate,
    get_personal_acceptance_probability,
)

logger = logging.getLogger("ownex.universal_evidence")


# ────────────────────────────────────────────────────────────────
# Universal Evidence Record — extends existing for all categories
# ────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class UniversalEvidenceRecord:
    """One evidence evaluation for ANY category."""

    opportunity_id: str
    category: str  # bug_bounty, dev_bounty, ai_training, etc.
    probability_type: str  # which ProbabilityType was evaluated
    evidence_scores: dict[str, float]  # e.g., {"validity": 0.85, "uniqueness": 0.9}
    checks: dict[str, bool]  # e.g., {"validity": true, "uniqueness": false}
    status: str  # NOT_READY | NEEDS_EVIDENCE | NEEDS_UNIQUENESS | HIGH_CONFIDENCE | READY_FOR_HUMAN_REVIEW
    evidence_label: str  # NO_EVIDENCE | THIN_EVIDENCE | SUFFICIENT_EVIDENCE | HIGH_EVIDENCE
    confidence: str  # none | low | medium | high | very_high
    notes: list[str] = field(default_factory=list)
    recorded_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UniversalEvidenceRecord:
        return cls(**data)


# ────────────────────────────────────────────────────────────────
# Category-Specific Evidence Evaluators
# ────────────────────────────────────────────────────────────────


class BaseEvidenceEvaluator:
    """Base class for category-specific evidence evaluation."""

    def __init__(self):
        self.acceptance_engine = get_personal_acceptance_probability()
        self.min_validity = 0.7
        self.min_uniqueness = 0.6
        self.min_evidence_score = 0.7
        self.min_acceptance = 0.90
        self.min_scope_verified = True

    def evaluate(self, opportunity: Any, evidence: Any) -> dict[str, Any]:
        """Evaluate evidence for an opportunity. Returns check results."""
        raise NotImplementedError


class BugBountyEvidenceEvaluator(BaseEvidenceEvaluator):
    """Evidence evaluator for Bug Bounty category."""

    def __init__(self):
        super().__init__()
        self.min_validity = 0.7
        self.min_uniqueness = 0.6
        self.min_evidence_score = 0.7
        self.min_acceptance = 0.90

    def evaluate(self, opportunity: Any, evidence: Any) -> dict[str, Any]:
        """Evaluate bug bounty evidence using existing EvidenceGate logic."""
        try:
            gate = get_evidence_gate()
            state = gate.evaluate(opportunity, evidence)
            return {
                "checks": {
                    "validity": state.checks.get("validity", False),
                    "uniqueness": state.checks.get("uniqueness", False),
                    "scope": state.checks.get("scope", False),
                    "evidence": state.checks.get("evidence", False),
                    "acceptance": state.checks.get("acceptance", False),
                    "confidence": state.checks.get("confidence", False),
                },
                "scores": {
                    "p_valid": state.p_valid,
                    "p_unique": state.p_unique,
                    "p_accept": state.p_accept,
                    "p_reward": state.p_reward,
                },
                "status": state.status,
                "p_accept_lower": state.p_accept_lower,
                "confidence": state.confidence,
                "notes": state.notes,
            }
        except Exception as exc:
            logger.warning("BugBountyEvidenceEvaluator failed: %s", exc)
            return {"status": "ERROR", "error": str(exc)}


class DevBountyEvidenceEvaluator(BaseEvidenceEvaluator):
    """Evidence evaluator for Dev Bounty category."""

    def __init__(self):
        super().__init__()
        self.min_validity = 0.5  # Less strict than bug bounty
        self.min_uniqueness = 0.5
        self.min_evidence_score = 0.6

    def evaluate(self, opportunity: Any, evidence: Any) -> dict[str, Any]:
        """Evaluate dev bounty evidence: repo health, issue clarity, test coverage."""
        try:
            est = self.acceptance_engine.estimate(
                niche="dev_bounty",
                platform=self._get_platform(opportunity),
                program=self._get_program(opportunity),
            )

            # Evidence scores from opportunity/evidence
            validity_score = min(1.0, getattr(evidence, "code_quality_score", 0.5))
            uniqueness_score = min(1.0, getattr(evidence, "originality_score", 0.5))
            evidence_score = min(1.0, getattr(evidence, "completeness_score", 0.5))

            checks = {
                "validity": validity_score >= 0.5,
                "uniqueness": uniqueness_score >= 0.5,
                "evidence": evidence_score >= 0.6,
                "acceptance": est.p_accept >= 0.85,  # Slightly lower than bug bounty
            }

            passed = sum(checks.values())
            if passed == 4:
                status = "HIGH_CONFIDENCE"
            elif passed >= 3 and checks["acceptance"]:
                status = "READY_FOR_HUMAN_REVIEW"
            elif passed >= 2:
                status = "NEEDS_EVIDENCE"
            else:
                status = "NOT_READY"

            return {
                "checks": checks,
                "scores": {
                    "p_valid": validity_score,
                    "p_unique": uniqueness_score,
                    "p_accept": est.p_accept,
                },
                "status": status,
                "p_accept_lower": est.p_accept_lower,
                "confidence": "high" if passed == 4 else "medium" if passed >= 3 else "low",
                "notes": [f"Dev bounty: validity={validity_score:.0%}, uniqueness={uniqueness_score:.0%}"],
            }
        except Exception as exc:
            logger.warning("DevBountyEvidenceEvaluator failed: %s", exc)
            return {"status": "ERROR", "error": str(exc)}

    def _get_platform(self, opportunity: Any) -> str:
        plat = getattr(opportunity, "platform", None)
        if plat is None:
            return ""
        if hasattr(plat, "value"):
            return plat.value
        return str(plat).strip().lower()

    def _get_program(self, opportunity: Any) -> str:
        prog = getattr(opportunity, "program", None)
        if prog is None:
            return ""
        if hasattr(prog, "value"):
            return prog.value
        return str(prog).strip().lower()


class AITrainingEvidenceEvaluator(BaseEvidenceEvaluator):
    """Evidence evaluator for AI Training / Data Annotation category."""

    def __init__(self):
        super().__init__()
        self.min_validity = 0.6
        self.min_uniqueness = 0.4
        self.min_evidence_score = 0.6

    def evaluate(self, opportunity: Any, evidence: Any) -> dict[str, Any]:
        """Evaluate AI training evidence: qualification pass, task quality, platform reliability."""
        try:
            est = self.acceptance_engine.estimate(
                niche="ai_training",
                platform=self._get_platform(opportunity),
                program=self._get_program(opportunity),
            )

            # Evidence scores specific to AI training
            qualification_score = min(1.0, getattr(evidence, "qualification_score", 0.5))
            task_quality_score = min(1.0, getattr(evidence, "task_quality_score", 0.5))
            platform_reliability = min(1.0, getattr(evidence, "platform_reliability", 0.7))

            checks = {
                "eligibility": qualification_score >= 0.6,
                "quality": task_quality_score >= 0.6,
                "platform": platform_reliability >= 0.6,
                "acceptance": est.p_accept >= 0.90,
            }

            passed = sum(checks.values())
            if passed == 4:
                status = "HIGH_CONFIDENCE"
            elif passed >= 3 and checks["acceptance"]:
                status = "READY_FOR_HUMAN_REVIEW"
            elif passed >= 2:
                status = "NEEDS_EVIDENCE"
            else:
                status = "NOT_READY"

            return {
                "checks": checks,
                "scores": {
                    "p_eligible": qualification_score,
                    "p_qualified": task_quality_score,
                    "p_completion": platform_reliability,
                    "p_accept": est.p_accept,
                    "p_payment": 0.95,  # Platform usually pays
                },
                "status": status,
                "confidence": "high" if passed == 4 else "medium" if passed >= 3 else "low",
                "notes": [f"AI Training: qualified={qualification_score:.0%}, quality={task_quality_score:.0%}"],
            }
        except Exception as exc:
            logger.warning("AITrainingEvidenceEvaluator failed: %s", exc)
            return {"status": "ERROR", "error": str(exc)}

    def _get_platform(self, opportunity: Any) -> str:
        plat = getattr(opportunity, "platform", None)
        if plat is None:
            return ""
        if hasattr(plat, "value"):
            return plat.value
        return str(plat).strip().lower()

    def _get_program(self, opportunity: Any) -> str:
        prog = getattr(opportunity, "program", None)
        if prog is None:
            return ""
        if hasattr(prog, "value"):
            return prog.value
        return str(prog).strip().lower()


class ClientWorkEvidenceEvaluator(BaseEvidenceEvaluator):
    """Evidence evaluator for Client Work / Freelance category."""

    def evaluate(self, opportunity: Any, evidence: Any) -> dict[str, Any]:
        """Evaluate client work evidence: client legitimacy, scope clarity, payment terms."""
        try:
            checks = {
                "lead": True,  # Lead already verified
                "reply": getattr(evidence, "client_reply_rate", 0.0) > 0.3,
                "qualified": getattr(evidence, "scope_clarity", 0.0) >= 0.7,
                "proposal": getattr(evidence, "proposal_quality", 0.0) >= 0.7,
                "acceptance": getattr(evidence, "client_acceptance_prob", 0.0) >= 0.8,
                "delivery": getattr(evidence, "delivery_confidence", 0.0) >= 0.8,
                "payment": getattr(evidence, "payment_terms_score", 0.0) >= 0.8,
            }

            passed = sum(checks.values())
            if passed == 7:
                status = "HIGH_CONFIDENCE"
            elif passed >= 5 and checks["acceptance"] and checks["payment"]:
                status = "READY_FOR_HUMAN_REVIEW"
            elif passed >= 4:
                status = "NEEDS_EVIDENCE"
            else:
                status = "NOT_READY"

            return {
                "checks": checks,
                "status": status,
                "confidence": "high" if passed == 7 else "medium" if passed >= 5 else "low",
                "notes": [f"Client work: {passed}/7 checks passed"],
            }
        except Exception as exc:
            logger.warning("ClientWorkEvidenceEvaluator failed: %s", exc)
            return {"status": "ERROR", "error": str(exc)}


class EmploymentEvidenceEvaluator(BaseEvidenceEvaluator):
    """Evidence evaluator for Employment category."""

    def evaluate(self, opportunity: Any, evidence: Any) -> dict[str, Any]:
        """Evaluate employment evidence: skills match, interview performance, offer quality."""
        try:
            checks = {
                "eligibility": getattr(evidence, "skills_match", 0.0) >= 0.7,
                "application": getattr(evidence, "application_quality", 0.0) >= 0.7,
                "response": getattr(evidence, "response_rate", 0.0) > 0.3,
                "interview": getattr(evidence, "interview_performance", 0.0) >= 0.7,
                "offer": getattr(evidence, "offer_quality", 0.0) >= 0.7,
                "retention": getattr(evidence, "retention_probability", 0.0) >= 0.8,
            }

            passed = sum(checks.values())
            if passed == 6:
                status = "HIGH_CONFIDENCE"
            elif passed >= 4 and checks["offer"]:
                status = "READY_FOR_HUMAN_REVIEW"
            elif passed >= 3:
                status = "NEEDS_EVIDENCE"
            else:
                status = "NOT_READY"

            return {
                "checks": checks,
                "status": status,
                "confidence": "high" if passed == 6 else "medium" if passed >= 4 else "low",
                "notes": [f"Employment: {passed}/6 checks passed"],
            }
        except Exception as exc:
            logger.warning("EmploymentEvidenceEvaluator failed: %s", exc)
            return {"status": "ERROR", "error": str(exc)}


class InvestmentEvidenceEvaluator(BaseEvidenceEvaluator):
    """Evidence evaluator for Investment category."""

    def evaluate(self, opportunity: Any, evidence: Any) -> dict[str, Any]:
        """Evaluate investment evidence: thesis quality, risk, liquidity."""
        try:
            checks = {
                "thesis": getattr(evidence, "thesis_quality", 0.0) >= 0.7,
                "execution": getattr(evidence, "execution_feasibility", 0.0) >= 0.7,
                "return": getattr(evidence, "expected_return", 0.0) >= 0.1,
                "risk": getattr(evidence, "risk_score", 1.0) <= 0.3,
                "drawdown": getattr(evidence, "max_drawdown", 1.0) <= 0.2,
            }

            passed = sum(checks.values())
            if passed == 5:
                status = "HIGH_CONFIDENCE"
            elif passed >= 3 and checks["thesis"] and checks["execution"]:
                status = "READY_FOR_HUMAN_REVIEW"
            elif passed >= 2:
                status = "NEEDS_EVIDENCE"
            else:
                status = "NOT_READY"

            return {
                "checks": checks,
                "status": status,
                "confidence": "high" if passed == 5 else "medium" if passed >= 3 else "low",
                "notes": [f"Investment: {passed}/5 checks passed"],
            }
        except Exception as exc:
            logger.warning("InvestmentEvidenceEvaluator failed: %s", exc)
            return {"status": "ERROR", "error": str(exc)}


# ────────────────────────────────────────────────────────────────
# Universal Evidence Engine — Routes to category-specific evaluators
# ────────────────────────────────────────────────────────────────


class UniversalEvidenceEngine:
    """
    Routes evidence evaluation to category-specific evaluators.

    This is the routing layer — actual evaluation logic lives in
    category-specific evaluators (BugBountyEvidenceEvaluator, etc.).
    """

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(os.environ.get("OWNEX_DATA_DIR", "data"))
        self.evidence_path = self.data_dir / "learning" / "universal_evidence.jsonl"
        self.evidence_path.parent.mkdir(parents=True, exist_ok=True)

        # Category-specific evaluators
        self._evaluators: dict[str, BaseEvidenceEvaluator] = {
            "bug_bounty": BugBountyEvidenceEvaluator(),
            "dev_bounty": DevBountyEvidenceEvaluator(),
            "ai_training": AITrainingEvidenceEvaluator(),
            "client_work": ClientWorkEvidenceEvaluator(),
            "employment": EmploymentEvidenceEvaluator(),
            "investment": InvestmentEvidenceEvaluator(),
        }

        # Legacy EvidenceGate for backward compatibility
        self.bug_bounty_gate = EvidenceGate()

        logger.info("UniversalEvidenceEngine initialized with all evaluators")

    # ─── Public API ─────────────────────────────────────────────────

    def evaluate(self, opportunity: Any, evidence: Any) -> dict[str, Any]:
        """Evaluate evidence for an opportunity using category-specific evaluator."""
        category = self._get_category(opportunity)
        evaluator = self._evaluators.get(category)

        if evaluator is None:
            logger.warning("No evaluator for category: %s", category)
            return {"status": "ERROR", "error": f"No evaluator for category: {category}"}

        try:
            result = evaluator.evaluate(opportunity, evidence)
            # Persist evaluation record
            self._record_evaluation(opportunity, category, result)
            return result
        except Exception as exc:
            logger.error("Evidence evaluation failed for %s: %s", category, exc)
            return {"status": "ERROR", "error": str(exc)}

    def evaluate_bug_bounty(self, opportunity: Any, evidence: Any) -> dict[str, Any]:
        """Convenience method for bug bounty (uses existing EvidenceGate)."""
        try:
            gate = get_evidence_gate()
            state = gate.evaluate(opportunity, evidence)
            return {
                "checks": state.checks,
                "scores": {
                    "p_valid": state.p_valid,
                    "p_unique": state.p_unique,
                    "p_accept": state.p_accept,
                    "p_reward": state.p_reward,
                },
                "status": state.status,
                "p_accept_lower": state.p_accept_lower,
                "confidence": state.confidence,
                "notes": state.notes,
            }
        except Exception as exc:
            logger.warning("Bug bounty evidence evaluation failed: %s", exc)
            return {"status": "ERROR", "error": str(exc)}

    def get_evaluator(self, category: str) -> BaseEvidenceEvaluator | None:
        """Get evaluator for a category."""
        return self._evaluators.get(category)

    def register_evaluator(self, category: str, evaluator: BaseEvidenceEvaluator) -> None:
        """Register a custom evaluator for a category."""
        self._evaluators[category] = evaluator
        logger.info("Registered custom evaluator for category: %s", category)

    # ─── Internal ───────────────────────────────────────────────────

    def _get_category(self, opportunity: Any) -> str:
        """Extract category from opportunity object."""
        cat = getattr(opportunity, "category", None)
        if cat is None:
            return "unknown"
        if hasattr(cat, "value"):
            return cat.value
        return str(cat).strip().lower().replace("opportunitycategory.", "")

    def _record_evaluation(self, opportunity: Any, category: str, result: dict[str, Any]) -> None:
        """Persist evidence evaluation record for learning/calibration."""
        try:
            record = {
                "opportunity_id": getattr(opportunity, "id", "unknown"),
                "category": category,
                "result": result,
                "recorded_at": datetime.now(UTC).isoformat(),
            }
            self.evidence_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.evidence_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("Failed to record evidence evaluation: %s", exc)


# ────────────────────────────────────────────────────────────────
# Singleton
# ────────────────────────────────────────────────────────────────

_universal_evidence: UniversalEvidenceEngine | None = None


def get_universal_evidence_engine(
    data_dir: str | Path | None = None,
) -> UniversalEvidenceEngine:
    """Get or create the universal evidence engine singleton."""
    global _universal_evidence
    if _universal_evidence is None or data_dir is not None:
        _universal_evidence = UniversalEvidenceEngine(data_dir)
    return _universal_evidence
