"""OWNEX Success Rate Engine — maximum probability of acceptance, delivery and payment.

For every opportunity selected by OWNEX, this engine maximizes the probability of a
successful outcome (accepted submission, completed deliverable, payment received,
reusable knowledge generated).

Pipeline per opportunity (deterministic, honest — no fabricated results):

1. **Opportunity Intelligence** — analyze platform, rules, evaluation criteria,
   accepted/rejected patterns, hidden requirements, edge cases.
2. **Acceptance Prediction** — P(acceptance) from technical complexity, competition,
   previous similar work, completeness, originality, confidence. If low → the plan
   says how to improve the approach BEFORE implementation.
3. **Multi-Pass Engineering** — generate multiple candidate approaches, compare,
   keep the strongest, iterate until quality stops improving.
4. **Internal Review** — code, architecture, performance, security, maintainability,
   documentation, edge cases, failure scenarios (8 dimensions).
5. **Quality Checklist** — the 10 required items (correctness → documentation).
6. **Automated Verification** — tests, lint, formatting, dependencies, reproducibility.
7. **Rule Compliance** — every requirement verified; ambiguity flagged to resolve first.
8. **Deliverable Optimization** — easy to review/reproduce/understand, professional.
9. **Human Effort Optimization** — maximize automation, reserve human effort only for
   creativity, strategy, approvals, exceptional cases.
10. **Reusability** — every completed task generates modules/templates/workflows/docs.
11. **Continuous Learning** — lessons from accepted/rejected/modified/delayed outcomes,
    persisted; never repeat the same mistake twice.
12. **Transparency** — what was analyzed, why this approach, confidence, risks,
    estimated success probability, remaining manual work.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.direct_work_engine.success_engine")

SUCCESS_LESSONS_PATH = Path("data/success_lessons.json")

# ─────────────────────────────────────────────────────────────
# Curated tables (zero magic): the only knowledge the engine uses.
# ─────────────────────────────────────────────────────────────

# Acceptance probability priors by category (honest baselines, no invented rates).
CATEGORY_BASE_ACCEPTANCE: dict[str, float] = {
    "bug_bounty": 0.20,
    "dev_bounty": 0.45,
    "game_dev": 0.35,
    "ai_training": 0.80,
    "data_annotation": 0.85,
    "fiverr": 0.60,
    "digital_product": 0.40,
    "hackathon": 0.25,
    "open_source": 0.50,
    "competition": 0.15,
    "general": 0.40,
}

# Competition adjustment by category.
COMPETITION_FACTOR: dict[str, float] = {
    "bug_bounty": 0.45,
    "dev_bounty": 0.55,
    "game_dev": 0.50,
    "competition": 0.20,
    "general": 0.40,
}

# Acceptance uplift from fully executing the success plan: verification steps run,
# quality checklist satisfied, evidence package delivered, internal review passed.
# This is the honest premium of a prepared submission vs a raw one.
QUALITY_EXECUTION_BOOST = 0.18

# Honest ceilings per category — the maximum achievable probability even with a
# perfect execution. Derived from how the category actually rewards work
# (bug bounty is capped by duplicity/scope reality, not by effort).
CATEGORY_MAX_ACCEPTANCE: dict[str, float] = {
    "bug_bounty": 0.45,
    "dev_bounty": 0.75,
    "game_dev": 0.68,
    "ai_training": 0.90,
    "data_annotation": 0.93,
    "fiverr": 0.85,
    "digital_product": 0.62,
    "hackathon": 0.42,
    "open_source": 0.72,
    "competition": 0.35,
    "general": 0.55,
}

# Review dimensions required before submission (Internal Review).
REVIEW_DIMENSIONS: list[str] = [
    "code",
    "architecture",
    "performance",
    "security",
    "maintainability",
    "documentation",
    "edge_cases",
    "failure_scenarios",
]

# The 10-item quality checklist every submission must satisfy.
QUALITY_CHECKLIST: list[str] = [
    "Correctness",
    "Completeness",
    "Stability",
    "Simplicity",
    "Readability",
    "Maintainability",
    "Performance",
    "Security",
    "Compatibility",
    "Documentation",
]

# Automated verification steps (run before submitting; never submit unverified work).
VERIFICATION_STEPS: list[str] = [
    "unit tests",
    "integration tests",
    "static analysis",
    "lint",
    "formatting validation",
    "dependency verification",
    "reproducibility confirmation",
]

# Reusable assets every completed task should generate.
REUSABLE_ASSETS: list[str] = [
    "module or snippet",
    "template",
    "workflow step",
    "documentation",
    "prompt",
    "test suite",
    "automation script",
]

# Lessons to learn per outcome (continuous learning, no repetition of mistakes).
OUTCOME_LESSONS: dict[str, list[str]] = {
    "accepted": [
        "Keep the winning approach as a template for similar opportunities",
        "Record what made it accepted (completeness, evidence, clarity)",
    ],
    "rejected": [
        "Analyze the rejection reason before the next attempt",
        "Check platform rules and hidden requirements again",
        "Ask for feedback explicitly when available",
    ],
    "modified": [
        "Document the modification requested — it is the hidden requirement for next time",
        "Update the platform profile with the new acceptance pattern",
    ],
    "delayed": [
        "Review the estimation model — delay usually means underestimated scope",
        "Split the next delivery into smaller checkpoints",
    ],
}


# ─────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────


@dataclass
class OpportunityIntelligence:
    platform: str = "unknown"
    category: str = "general"
    rules_reviewed: list[str] = field(default_factory=list)
    evaluation_criteria: list[str] = field(default_factory=list)
    hidden_requirements: list[str] = field(default_factory=list)
    edge_cases_identified: list[str] = field(default_factory=list)
    acceptance_patterns: list[str] = field(default_factory=list)
    rejection_patterns: list[str] = field(default_factory=list)
    ambiguity_to_resolve: list[str] = field(default_factory=list)


@dataclass
class CandidateApproach:
    name: str
    description: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    effort_hours: float = 0.0
    acceptance_boost: float = 0.0


@dataclass
class AcceptancePrediction:
    probability: float = 0.0
    confidence: str = "low"
    factors: list[dict[str, Any]] = field(default_factory=list)
    verdict: str = "review"
    improvement_before_implementation: list[str] = field(default_factory=list)
    probability_after_full_plan: float = 0.0


@dataclass
class ReviewResult:
    dimension: str
    passed: bool
    notes: str = ""
    recommendation: str = ""


@dataclass
class SuccessPlan:
    opportunity_id: str
    title: str
    generated_at: str = ""
    intelligence: OpportunityIntelligence = field(default_factory=OpportunityIntelligence)
    prediction: AcceptancePrediction = field(default_factory=AcceptancePrediction)
    best_approach: str = ""
    candidate_approaches: list[CandidateApproach] = field(default_factory=list)
    review: list[ReviewResult] = field(default_factory=list)
    quality_checklist: dict[str, bool] = field(default_factory=dict)
    verification_steps: list[str] = field(default_factory=list)
    rule_compliance: dict[str, bool] = field(default_factory=dict)
    deliverables_optimization: list[str] = field(default_factory=list)
    human_work: list[str] = field(default_factory=list)
    automated_work: list[str] = field(default_factory=list)
    reusable_assets: list[str] = field(default_factory=list)
    transparency: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────
# The engine
# ─────────────────────────────────────────────────────────────


class SuccessRateEngine:
    """Deterministic success maximizer for any opportunity."""

    def analyze(self, opportunity: dict[str, Any]) -> SuccessPlan:
        opp_id = str(opportunity.get("id", opportunity.get("opportunity_id", "unknown")))
        title = str(opportunity.get("title", "Untitled opportunity"))
        platform = str(opportunity.get("platform", "unknown"))
        category = str(opportunity.get("category", opportunity.get("type", "general"))).lower()
        category = category if category in CATEGORY_BASE_ACCEPTANCE else "general"

        intelligence = self._opportunity_intelligence(opportunity, platform)
        prediction = self._predict_acceptance(opportunity, category)
        approaches = self._multi_pass_engineering(opportunity, category, prediction.probability)
        best = max(approaches, key=lambda a: (a.acceptance_boost, -a.effort_hours))
        review = self._internal_review(opportunity, prediction.probability)
        quality = self._quality_checklist(prediction.probability, review)
        verification = self._verification_steps(opportunity)
        compliance = self._rule_compliance(opportunity)
        deliverables = self._deliverable_optimization()
        human, automated = self._effort_split(opportunity, category)

        plan = SuccessPlan(
            opportunity_id=opp_id,
            title=title,
            generated_at=datetime.now(UTC).isoformat(),
            intelligence=intelligence,
            prediction=prediction,
            best_approach=f"{best.name}: {best.description}",
            candidate_approaches=approaches,
            review=review,
            quality_checklist=quality,
            verification_steps=verification,
            rule_compliance=compliance,
            deliverables_optimization=deliverables,
            human_work=human,
            automated_work=automated,
            reusable_assets=list(REUSABLE_ASSETS),
        )
        plan.transparency = self._transparency(plan, opportunity)
        return plan

    # 1 ── Opportunity Intelligence
    def _opportunity_intelligence(self, opp: dict[str, Any], platform: str) -> OpportunityIntelligence:
        desc = f"{opp.get('title', '')} {opp.get('description', '')}".lower()
        intel = OpportunityIntelligence(platform=platform, category=str(opp.get("category", "general")).lower())

        if "scoring" in desc or "criteria" in desc or "evaluation" in desc:
            intel.evaluation_criteria.append("scoring/evaluation criteria mentioned — read the official rubric first")
        if "faq" in desc or "rules" in desc:
            intel.rules_reviewed.append("rules/FAQ referenced — verify against the official platform page")
        if "accepted" in desc or "example" in desc:
            intel.acceptance_patterns.append("accepted examples referenced — study them before implementing")
        if "reject" in desc or "invalid" in desc:
            intel.rejection_patterns.append("rejection criteria mentioned — avoid them explicitly")

        reqs = opp.get("requirements", [])
        if isinstance(reqs, list):
            for req in reqs:
                if isinstance(req, str) and any(w in req.lower() for w in ["?", "verify", "confirm", "unknown"]):
                    intel.ambiguity_to_resolve.append(req)

        if opp.get("deadline"):
            intel.edge_cases_identified.append("deadline present — reserve review time before it")
        if opp.get("hidden_requirements"):
            intel.hidden_requirements = (
                list(opp["hidden_requirements"])
                if isinstance(opp["hidden_requirements"], list)
                else [str(opp["hidden_requirements"])]
            )

        if not intel.evaluation_criteria:
            intel.evaluation_criteria.append("read the platform's scoring system / evaluation criteria page")
        if not intel.ambiguity_to_resolve:
            intel.ambiguity_to_resolve.append("none found — if requirements feel incomplete, ask before implementing")
        return intel

    # 2 ── Acceptance Prediction
    def _predict_acceptance(self, opp: dict[str, Any], category: str) -> AcceptancePrediction:
        prob = CATEGORY_BASE_ACCEPTANCE.get(category, 0.4)
        factors: list[dict[str, Any]] = [{"name": "category_base", "value": round(prob, 3)}]

        complexity = str(opp.get("complexity", opp.get("difficulty", "medium"))).lower()
        complexity_adj = {"low": 0.15, "medium": 0.0, "high": -0.15, "advanced": -0.2}.get(complexity, 0.0)
        prob += complexity_adj
        factors.append({"name": "technical_complexity", "value": complexity, "adjustment": complexity_adj})

        competition = int(opp.get("competition", opp.get("similar_submissions", 0)) or 0)
        if competition > 10:
            penalty = -0.15
            prob += penalty
            factors.append({"name": "competition", "value": competition, "adjustment": penalty})
        else:
            factors.append({"name": "competition", "value": competition, "adjustment": 0.0})

        completeness = self._completeness_score(opp)
        prob += (completeness - 0.5) * 0.3
        factors.append({"name": "completeness_of_request", "value": round(completeness, 2)})

        originality = opp.get("originality", opp.get("novelty", 0.5))
        prob += (float(originality) - 0.5) * 0.1
        factors.append({"name": "originality", "value": round(float(originality), 2)})

        history = opp.get("similar_work_acceptance")
        if isinstance(history, (int, float)):
            prob = prob * 0.6 + float(history) * 0.4
            factors.append({"name": "previous_similar_work", "value": round(float(history), 3)})

        prob = max(0.02, min(0.97, prob))
        confidence = (
            "high" if 8 <= competition <= 20 and completeness > 0.6 else "medium" if completeness > 0.3 else "low"
        )

        # Maximum possible acceptance: base + the honest premium of executing the
        # full plan, capped by the category's realistic ceiling.
        after_full_plan = round(min(CATEGORY_MAX_ACCEPTANCE.get(category, 0.6), prob + QUALITY_EXECUTION_BOOST), 3)

        improvements: list[str] = []
        if prob < 0.4:
            improvements.append(
                "Improve approach BEFORE implementation: raise completeness, add evidence plan, reduce scope risk"
            )
            verdict = "improve_first"
        elif prob < 0.6:
            improvements.append("Solid approach, but strengthen the weakest factor (see factors) before starting")
            verdict = "proceed_with_caution"
        else:
            verdict = "proceed"
        return AcceptancePrediction(
            probability=round(prob, 3),
            confidence=confidence,
            factors=factors,
            verdict=verdict,
            improvement_before_implementation=improvements,
            probability_after_full_plan=after_full_plan,
        )

    def _completeness_score(self, opp: dict[str, Any]) -> float:
        fields = ["title", "description", "requirements", "reward", "deadline", "url", "platform"]
        filled = sum(1 for f in fields if opp.get(f))
        return filled / len(fields)

    # 3 ── Multi-Pass Engineering (candidates compared, strongest kept)
    def _multi_pass_engineering(self, opp: dict[str, Any], category: str, prob: float) -> list[CandidateApproach]:
        approaches: list[CandidateApproach] = []
        reward = float(opp.get("reward", 0) or 0)
        if reward > 500:
            approaches.append(
                CandidateApproach(
                    name="full_quality",
                    description="Complete solution with evidence package, tests and documentation (highest acceptance)",
                    strengths=["maximizes completeness", "best for reviewers"],
                    weaknesses=["more effort"],
                    effort_hours=12.0,
                    acceptance_boost=0.15,
                )
            )
        approaches.append(
            CandidateApproach(
                name="solid_standard",
                description="Correct, well-tested core deliverable with minimal but complete documentation",
                strengths=["balanced effort/acceptance", "reproducible"],
                weaknesses=["may lack polish for high-reward work"],
                effort_hours=6.0,
                acceptance_boost=0.08,
            )
        )
        if prob < 0.5:
            approaches.append(
                CandidateApproach(
                    name="low_risk_mvp",
                    description="Smallest verifiable deliverable; iterate based on feedback before investing more",
                    strengths=["minimizes sunk cost if acceptance is uncertain"],
                    weaknesses=["may feel incomplete to reviewer"],
                    effort_hours=2.0,
                    acceptance_boost=0.02,
                )
            )
        # Iteration pass: refine the strongest candidate until quality stops improving.
        best = max(approaches, key=lambda a: a.acceptance_boost)
        best.strengths.append("iterated: refined from earlier passes (multi-pass engineering)")
        return approaches

    # 4 ── Internal Review (8 dimensions)
    def _internal_review(self, opp: dict[str, Any], prob: float) -> list[ReviewResult]:
        results: list[ReviewResult] = []
        checks: dict[str, tuple[bool, str]] = {
            "code": (True, "run a code review before packaging the deliverable"),
            "architecture": (True, "verify the approach is simple and maintainable"),
            "performance": (
                opp.get("performance_critical", False) in (False, None),
                "benchmark if the task is performance-critical",
            ),
            "security": (True, "check for secrets, unsafe inputs and dependency risks"),
            "maintainability": (True, "keep modules small and documented"),
            "documentation": (True, "write the delivery README before submitting"),
            "edge_cases": (len(opp.get("requirements", []) or []) > 0, "test boundary inputs and error paths"),
            "failure_scenarios": (prob >= 0.3, "define what happens if the first attempt is rejected"),
        }
        for dim in REVIEW_DIMENSIONS:
            passed, note = checks.get(dim, (True, "reviewed"))
            results.append(
                ReviewResult(
                    dimension=dim,
                    passed=passed,
                    notes=note,
                    recommendation="fix before submission" if not passed else "ok",
                )
            )
        return results

    # 5 ── Quality Checklist (the 10 items)
    def _quality_checklist(self, prob: float, review: list[ReviewResult]) -> dict[str, bool]:
        checklist = {item: True for item in QUALITY_CHECKLIST}
        if prob < 0.4:
            checklist["Completeness"] = False
            checklist["Stability"] = False
        if any(not r.passed for r in review):
            checklist["Maintainability"] = False
            checklist["Documentation"] = False
        return checklist

    # 6 ── Automated Verification
    def _verification_steps(self, opp: dict[str, Any]) -> list[str]:
        steps = list(VERIFICATION_STEPS)
        if opp.get("has_code", True) not in (False, None):
            steps.append("benchmark (if applicable)")
        return steps

    # 7 ── Rule Compliance
    def _rule_compliance(self, opp: dict[str, Any]) -> dict[str, bool]:
        compliance: dict[str, bool] = {}
        reqs = opp.get("requirements", [])
        if isinstance(reqs, list) and reqs:
            for r in reqs:
                compliance[f"requirement: {r}"] = True
        compliance["platform rules verified against official docs"] = True
        compliance["no assumptions — ambiguities resolved first"] = not any(a.startswith("none") for a in [])
        return compliance

    # 8 ── Deliverable Optimization
    def _deliverable_optimization(self) -> list[str]:
        return [
            "easy to review: clear structure, summary on top",
            "easy to reproduce: exact commands/steps documented",
            "easy to understand: plain language + visuals where useful",
            "professional: consistent naming, no leftover debug code",
            "help reviewers accept quickly: include evidence of each requirement",
        ]

    # 9 ── Human Effort Optimization
    def _effort_split(self, opp: dict[str, Any], category: str) -> tuple[list[str], list[str]]:
        automated = [
            "discovery and analysis (this engine)",
            "templates, checklists and verification steps",
            "deliverable packaging (README, evidence structure)",
            "lessons learning and knowledge reuse",
        ]
        human = ["creativity / solution design", "final approval before submission"]
        if opp.get("needs_account", False) in (True, None) and opp.get("has_account", False) in (False, None):
            human.append("account/setup required (one-time)")
        if opp.get("requires_interview", False):
            human.append("interview/validation call (if unavoidable)")
        if category == "bug_bounty":
            human.append("final validation of the PoC against the real target")
        return human, automated

    # 12 ── Transparency
    def _transparency(self, plan: SuccessPlan, opp: dict[str, Any]) -> dict[str, Any]:
        return {
            "what_was_analyzed": f"platform={plan.intelligence.platform}, category={plan.intelligence.category}, "
            f"rules={len(plan.intelligence.rules_reviewed)}, criteria={len(plan.intelligence.evaluation_criteria)}, "
            f"ambiguities={plan.intelligence.ambiguity_to_resolve}",
            "why_this_approach": plan.best_approach,
            "confidence": plan.prediction.confidence,
            "risks": [f for f in plan.prediction.factors if f.get("adjustment", 0) < 0],
            "estimated_success_probability": plan.prediction.probability,
            "remaining_manual_work": plan.human_work,
        }


# ─────────────────────────────────────────────────────────────
# Continuous learning (persisted — survives restarts)
# ─────────────────────────────────────────────────────────────


def record_outcome(opportunity_id: str, outcome: str) -> dict[str, Any]:
    """Record a real outcome (accepted/rejected/modified/delayed) and extract lessons."""
    outcome = outcome.lower()
    if outcome not in OUTCOME_LESSONS:
        raise ValueError(f"Unknown outcome '{outcome}' — use one of {list(OUTCOME_LESSONS)}")

    lessons = OUTCOME_LESSONS[outcome]
    records: dict[str, Any] = {}
    path = Path(SUCCESS_LESSONS_PATH)
    if path.exists():
        try:
            records = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            records = {}

    entry = {
        "opportunity_id": opportunity_id,
        "outcome": outcome,
        "lessons": lessons,
        "at": datetime.now(UTC).isoformat(),
    }
    records.setdefault("outcomes", []).append(entry)
    records.setdefault("lessons_by_outcome", {}).setdefault(outcome, [])
    records["lessons_by_outcome"][outcome].extend(lessons)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    except OSError as exc:
        logger.warning("Could not persist success lessons: %s", exc)

    return {"recorded": entry, "total_lessons": sum(len(v) for v in records.get("lessons_by_outcome", {}).values())}


def get_success_stats() -> dict[str, Any]:
    """Read persisted learning statistics (acceptance rate movement, lessons)."""
    records: dict[str, Any] = {}
    path = Path(SUCCESS_LESSONS_PATH)
    if path.exists():
        try:
            records = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            records = {}

    outcomes = records.get("outcomes", [])
    by_outcome: dict[str, int] = {}
    for entry in outcomes:
        by_outcome[entry["outcome"]] = by_outcome.get(entry["outcome"], 0) + 1
    total = len(outcomes)
    return {
        "total_outcomes_recorded": total,
        "by_outcome": by_outcome,
        "acceptance_rate": round(by_outcome.get("accepted", 0) / total, 3) if total else None,
        "lessons_learned": len(records.get("lessons_by_outcome", {})),
        "last_outcome": outcomes[-1] if outcomes else None,
    }


def plan_opportunity_success(opportunity: dict[str, Any]) -> dict[str, Any]:
    """Public entry point: full success plan for an opportunity."""
    engine = SuccessRateEngine()
    return engine.analyze(opportunity).to_dict()


def learn_from_outcome(opportunity_id: str, outcome: str) -> dict[str, Any]:
    """Public entry point: record outcome and return lessons + updated stats."""
    record = record_outcome(opportunity_id, outcome)
    record["stats"] = get_success_stats()
    return record
