"""Evolution & Income Intelligence — long-term learning layer of OWNEX.

Learns from every tracked outcome:
  * lost work  -> skill evolution lesson with a learning path
  * market     -> capability expansion proposals detected from real demand
  * history    -> performance analysis (conversion + ROI) per platform/category

Pure and decoupled: never invents facts absent from the inputs. Required skills
are curated once in ``cores/career_engine`` (single source of truth) and reused
here — no duplicated maps.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from cores.direct_work_engine.feedback import LearningRecord
from cores.direct_work_engine.models import Opportunity, UserProfile

logger = logging.getLogger("ownex.direct_work_engine.evolution")

# Required skills per category are curated once in cores.career_engine (single
# source of truth) and reused here — imported lazily to avoid a circular import
# through the direct_work_engine package __init__.
_CAREER_SKILLS: None | dict = None


def _required_skills() -> dict:
    global _CAREER_SKILLS
    if _CAREER_SKILLS is None:
        from cores.career_engine import CATEGORY_REQUIRED_SKILLS

        _CAREER_SKILLS = CATEGORY_REQUIRED_SKILLS
    return _CAREER_SKILLS


def _skill_key(value: object) -> str:
    return str(value).strip().lower()


# ---------------------------------------------------------------------------
# 1. Skill Evolution — learn from lost opportunities
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LostOpportunityLesson:
    """Why an opportunity was lost and the concrete path to fix it."""

    platform: str
    category: str
    reason: str
    suggested_skills: list[str] = field(default_factory=list)
    learning_path: list[str] = field(default_factory=list)


class SkillEvolutionEngine:
    """Turns rejected work into a prioritized learning path.

    Uses the category's curated required skills (career engine) and only
    suggests skills the user does not already have — never invented ones.
    """

    def learn_from_lost(
        self,
        records: list[LearningRecord],
        profile: UserProfile,
    ) -> list[LostOpportunityLesson]:
        lost = [r for r in records if not r.accepted]
        if not lost:
            return []

        user_skills = {_skill_key(s) for s in (profile.skills or set())}

        lessons: list[LostOpportunityLesson] = []
        for record in lost:
            if record.category is None:
                continue
            required = _required_skills().get(record.category, set())
            missing = [s for s in required if _skill_key(s) not in user_skills]
            cat_label = record.category.value if hasattr(record.category, "value") else str(record.category)

            if not missing:
                lessons.append(
                    LostOpportunityLesson(
                        platform=record.platform,
                        category=cat_label,
                        reason="No faltaron skills del stack; revisar calidad de entrega o ajuste con el encargo.",
                        suggested_skills=[],
                        learning_path=["Repasar comunicación y presentación de la entrega"],
                    )
                )
                continue

            lessons.append(
                LostOpportunityLesson(
                    platform=record.platform,
                    category=cat_label,
                    reason=f"Missing {' / '.join(sorted(missing))}",
                    suggested_skills=list(missing),
                    learning_path=_build_learning_path(missing),
                )
            )

        logger.info("Skill evolution: %d lost opportunities -> %d lessons", len(lost), len(lessons))
        return lessons


def _build_learning_path(missing_skills: list[str]) -> list[str]:
    """One clear learning path from raw skills (e.g. docker -> containers -> deploy)."""
    path: list[str] = []
    if not missing_skills:
        return path
    for skill in missing_skills:
        path.append(f"Study the fundamentals of {skill}")
    path.append("Build a minimal production-style scaffold using the stack")
    path.append("Deploy it end-to-end until the pipeline is green")
    path.append("Ask OWNEX to review the diff before the next delivery")
    return path


# ---------------------------------------------------------------------------
# 2. Capability Expansion — detect missing abilities from real market demand
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CapabilityProposal:
    """A capability OWNEX detected the user lacks, backed by market evidence."""

    name: str
    evidence_count: int
    expected_benefit: str
    implementation: list[str] = field(default_factory=list)
    risk: str = ""
    maintenance_cost: str = ""


class CapabilityExpansionDetector:
    """Finds skills the market demands often but the user does not have yet.

    Every proposal includes reason (evidence count), benefit, implementation,
    risk and maintenance cost, per the Self-Improvement Rules of the spec.
    """

    MIN_EVIDENCE = 3

    def detect(
        self,
        opportunities: list[Opportunity],
        profile: UserProfile,
        min_evidence: int | None = None,
    ) -> list[CapabilityProposal]:
        if not opportunities:
            return []

        threshold = min_evidence or self.MIN_EVIDENCE
        user_skills = {_skill_key(s) for s in (profile.skills or set())}

        counts: Counter[str] = Counter()
        for opp in opportunities:
            for tag in opp.technology_tags or []:
                if tag:
                    counts[_skill_key(tag)] += 1

        proposals: list[CapabilityProposal] = []
        for skill, count in counts.most_common():
            if skill in user_skills or count < threshold:
                continue
            proposals.append(
                CapabilityProposal(
                    name=f"{skill.capitalize()} Integration",
                    evidence_count=count,
                    expected_benefit=f"Unlock compatibility with {count} detected opportunities instead of {count - 1}.",
                    implementation=[
                        f"Install/learn the {skill} toolchain",
                        f"Add {skill} to the knowledge base",
                        "Create a reusable workflow for it",
                    ],
                    risk="Low — additive capability, does not touch stable modules.",
                    maintenance_cost="Low — one curated workflow to keep updated.",
                )
            )
        return proposals


# ---------------------------------------------------------------------------
# 3. Performance Analysis — conversion + ROI from verified history
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PerformanceAnalysis:
    total: int = 0
    accepted: int = 0
    rejected: int = 0
    revenue: float = 0.0
    time_invested_hours: float = 0.0
    roi_usd_per_hour: float = 0.0
    conversion_rate: float = 0.0
    platform_conversion: dict[str, float] = field(default_factory=dict)
    category_conversion: dict[str, float] = field(default_factory=dict)
    top_platform_by_revenue: str = ""
    top_category_by_revenue: str = ""


class PerformanceAnalyzer:
    """Aggregates verified outcomes into conversion and ROI signals."""

    def analyze(
        self,
        records: list[LearningRecord],
        time_invested_hours: float = 0.0,
    ) -> PerformanceAnalysis:
        if not records:
            return PerformanceAnalysis()

        accepted = [r for r in records if r.accepted]
        rejected = [r for r in records if not r.accepted]
        revenue = round(sum(r.amount for r in accepted), 2)
        total = len(records)

        by_platform: dict[str, list[LearningRecord]] = defaultdict(list)
        by_category: dict[str, list[LearningRecord]] = defaultdict(list)
        for record in records:
            by_platform[record.platform].append(record)
            cat = record.category.value if record.category else ""
            if cat:
                by_category[cat].append(record)

        platform_revenue = {k: sum(r.amount for r in v if r.accepted) for k, v in by_platform.items()}
        category_revenue = {k: sum(r.amount for r in v if r.accepted) for k, v in by_category.items()}

        return PerformanceAnalysis(
            total=total,
            accepted=len(accepted),
            rejected=len(rejected),
            revenue=revenue,
            time_invested_hours=time_invested_hours,
            roi_usd_per_hour=round(revenue / time_invested_hours, 2) if time_invested_hours > 0 else 0.0,
            conversion_rate=round(len(accepted) / total, 3) if total else 0.0,
            platform_conversion={
                k: round(len([r for r in v if r.accepted]) / len(v), 3) for k, v in by_platform.items()
            },
            category_conversion={
                k: round(len([r for r in v if r.accepted]) / len(v), 3) for k, v in by_category.items()
            },
            top_platform_by_revenue=max(platform_revenue.items(), key=lambda kv: kv[1])[0] if platform_revenue else "",
            top_category_by_revenue=max(category_revenue.items(), key=lambda kv: kv[1])[0] if category_revenue else "",
        )


def evolve_analysis(
    lost_lessons: list[LostOpportunityLesson],
    proposals: list[CapabilityProposal],
    performance: PerformanceAnalysis,
) -> dict:
    """Package the three evolution signals into one report (self-improvement rules)."""
    return {
        "lessons": [
            {
                "platform": lesson.platform,
                "category": lesson.category,
                "reason": lesson.reason,
                "suggested_skills": lesson.suggested_skills,
                "learning_path": lesson.learning_path,
            }
            for lesson in lost_lessons
        ],
        "capabilities": [
            {
                "name": proposal.name,
                "evidence_count": proposal.evidence_count,
                "expected_benefit": proposal.expected_benefit,
                "implementation": proposal.implementation,
                "risk": proposal.risk,
                "maintenance_cost": proposal.maintenance_cost,
            }
            for proposal in proposals
        ],
        "performance": {
            "total": performance.total,
            "accepted": performance.accepted,
            "rejected": performance.rejected,
            "revenue": performance.revenue,
            "roi_usd_per_hour": performance.roi_usd_per_hour,
            "conversion_rate": performance.conversion_rate,
            "platform_conversion": performance.platform_conversion,
            "category_conversion": performance.category_conversion,
            "top_platform_by_revenue": performance.top_platform_by_revenue,
            "top_category_by_revenue": performance.top_category_by_revenue,
        },
    }
