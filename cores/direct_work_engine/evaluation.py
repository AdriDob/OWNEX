"""Direct Work Evaluation Engine — Quality gate and evaluation for work items.

Provides evaluation logic that can be used by WorkerCore for the VALIDATE phase.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from cores.direct_work_engine.filters import StrictFilter
from cores.direct_work_engine.models import Opportunity
from cores.direct_work_engine.profile_builder import IntelligentProfileBuilder
from cores.direct_work_engine.recommendation import IntelligentRecommender, RecommenderConfig
from cores.direct_work_engine.scoring import ZeroBarrierScorer

logger = logging.getLogger("ownex.direct_work_engine.evaluation")


@dataclass(slots=True)
class EvaluationResult:
    """Result of evaluating a work item."""

    passed: bool
    score: float
    reasons: list[str] = field(default_factory=list)
    barrier_score: float = 0.0
    expected_value_usd_per_hour: float = 0.0
    acceptance_probability: float = 0.0
    compatibility_score: float = 0.0
    speed_score: float = 0.0
    reputation_score: float = 0.0
    risk_score: float = 0.0
    strict_filter_rejected: bool = False
    strict_filter_reasons: list[str] = field(default_factory=list)
    quality_gate_result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "reasons": self.reasons,
            "barrier_score": self.barrier_score,
            "expected_value_usd_per_hour": self.expected_value_usd_per_hour,
            "acceptance_probability": self.acceptance_probability,
            "compatibility_score": self.compatibility_score,
            "speed_score": self.speed_score,
            "reputation_score": self.reputation_score,
            "risk_score": self.risk_score,
            "strict_filter_rejected": self.strict_filter_rejected,
            "strict_filter_reasons": self.strict_filter_reasons,
            "quality_gate_result": self.quality_gate_result,
        }


class DirectWorkEvaluationEngine:
    """Evaluates work items for quality and viability.

    Combines:
    - Zero-barrier scoring
    - Strict filtering
    - Quality gate validation (simplified)
    - Expected value calculation
    """

    def __init__(
        self,
        scorer: ZeroBarrierScorer | None = None,
        recommender: IntelligentRecommender | None = None,
        recommender_config: RecommenderConfig | None = None,
        profile_builder: IntelligentProfileBuilder | None = None,
        strict_filter: StrictFilter | None = None,
    ):
        self.scorer = scorer or ZeroBarrierScorer()
        self.recommender = recommender or IntelligentRecommender(config=RecommenderConfig())
        self.profile_builder = profile_builder or IntelligentProfileBuilder()
        self.strict_filter = StrictFilter()

    def evaluate(self, work_item: Any, profile: Any = None) -> dict[str, Any]:
        """Evaluate a work item and return evaluation result.

        Args:
            work_item: Work item with opportunity attributes
            profile: User profile (optional)

        Returns:
            Evaluation result dict
        """
        # Phase 1: Strict Filter (hard rejects)
        if hasattr(work_item, "opportunity_genome") and work_item.opportunity_genome:
            opportunity = work_item.opportunity_genome
        else:
            # Create minimal opportunity from work item
            opportunity = self._create_opportunity_from_work_item(work_item)

        filter_reasons = self.strict_filter.reject(opportunity)
        if filter_reasons:
            return EvaluationResult(
                passed=False,
                score=0.0,
                reasons=["Rejected by strict filter"],
                strict_filter_rejected=True,
                strict_filter_reasons=filter_reasons,
            ).to_dict()

        # Phase 2: Zero-barrier scoring
        scored = self.scorer.score_opportunities([opportunity])
        if not scored:
            return EvaluationResult(
                passed=False,
                score=0.0,
                reasons=["Scoring failed"],
            ).to_dict()

        scored_opp = scored[0]
        barrier_score = scored_opp.zero_barrier_score.total if scored_opp.zero_barrier_score else 0.0

        # Phase 3: Expected value and recommendation
        profile_obj = profile or self.profile_builder.build()
        ranked = self.recommender.recommend(scored, profile_obj, limit=1)

        if not ranked:
            return EvaluationResult(
                passed=False,
                score=0.0,
                reasons=["Recommendation failed"],
            ).to_dict()

        ranked_opp = ranked[0]
        overall_score = ranked_opp.overall_recommendation_score

        # Phase 4: Quality Gate — multi-signal check
        quality_gate_result = _run_quality_gate(work_item)

        if not quality_gate_result["passed"]:
            return EvaluationResult(
                passed=False,
                score=overall_score,
                reasons=[f"Quality gate failed: {quality_gate_result['reason']}"],
                barrier_score=barrier_score,
                expected_value_usd_per_hour=ranked_opp.expected_value,
                acceptance_probability=ranked_opp.acceptance_probability,
                compatibility_score=ranked_opp.compatibility_score,
                speed_score=ranked_opp.speed_score,
                reputation_score=ranked_opp.reputation_score,
                risk_score=ranked_opp.risk_score,
                quality_gate_result=quality_gate_result,
            ).to_dict()

        # Build reasons
        reasons = []
        if scored_opp.zero_barrier_score:
            reasons.extend(scored_opp.zero_barrier_score.enablers)
            reasons.extend([f"BLOCKER: {b}" for b in scored_opp.zero_barrier_score.blockers])

        if ranked_opp.recommendation_reasoning:
            reasons.extend(ranked_opp.recommendation_reasoning)

        return EvaluationResult(
            passed=True,
            score=overall_score,
            reasons=reasons,
            barrier_score=scored_opp.zero_barrier_score.total if scored_opp.zero_barrier_score else 0.0,
            expected_value_usd_per_hour=ranked_opp.expected_value,
            acceptance_probability=ranked_opp.acceptance_probability,
            compatibility_score=ranked_opp.compatibility_score,
            speed_score=ranked_opp.speed_score,
            reputation_score=ranked_opp.reputation_score,
            risk_score=ranked_opp.risk_score,
            strict_filter_rejected=False,
            quality_gate_result={"passed": True, "reason": "All checks passed"},
        ).to_dict()


def _create_opportunity_from_work_item(self, work_item: Any) -> Any:
    """Create a minimal Opportunity from work item."""

    return Opportunity(
        id=getattr(work_item, "id", "") or "unknown",
        title=getattr(work_item, "title", "") or "Untitled",
        platform=getattr(work_item, "platform", "") or "unknown",
        category=getattr(work_item, "category", "software_engineering"),
        payment=getattr(work_item, "reward", 0.0) or 0.0,
        estimated_time_hours=getattr(work_item, "estimated_hours", 1.0) or 1.0,
    )


def _run_quality_gate(work_item: Any) -> dict[str, Any]:
    """Run quality gate checks on a work item.

    Checks:
    1. Evidence present (required)
    2. Artifacts present (if applicable)
    3. No critical errors in execution
    4. Platform-specific requirements met
    """
    checks: list[dict[str, Any]] = []
    all_passed = True

    # Check 1: Evidence
    evidence = getattr(work_item, "evidence", []) or []
    if evidence:
        checks.append({"check": "evidence", "passed": True, "detail": f"{len(evidence)} evidence items"})
    else:
        checks.append({"check": "evidence", "passed": False, "detail": "No evidence provided"})
        all_passed = False

    # Check 2: Artifacts
    artifacts = getattr(work_item, "artifacts", []) or []
    if artifacts:
        checks.append({"check": "artifacts", "passed": True, "detail": f"{len(artifacts)} artifacts"})
    else:
        # Artifacts are optional — warn but don't block
        checks.append({"check": "artifacts", "passed": True, "detail": "No artifacts (non-blocking)"})

    # Check 3: No critical errors
    error = getattr(work_item, "error", None)
    if error:
        checks.append({"check": "no_errors", "passed": False, "detail": f"Error: {error}"})
        all_passed = False
    else:
        checks.append({"check": "no_errors", "passed": True, "detail": "No errors"})

    # Check 4: Has title/description
    title = getattr(work_item, "title", "")
    if title:
        checks.append({"check": "has_title", "passed": True, "detail": f"Title: {title[:50]}"})
    else:
        checks.append({"check": "has_title", "passed": False, "detail": "No title"})
        all_passed = False

    return {
        "passed": all_passed,
        "checks": checks,
        "passed_count": sum(1 for c in checks if c["passed"]),
        "total_count": len(checks),
        "reason": "All quality checks passed"
        if all_passed
        else next((c["detail"] for c in checks if not c["passed"]), "Quality gate failed"),
    }


# Convenience function for simple evaluation
async def evaluate_work_item(work_item: Any, profile: Any = None) -> dict[str, Any]:
    """Convenience function for evaluating a work item."""
    engine = DirectWorkEvaluationEngine()
    return engine.evaluate(work_item, profile)
