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


# ---------------------------------------------------------------------------
# 3b. Channel Economy — MONEY VALIDATION: personal empirical economy per
# channel. ACCEPTED is pipeline; only PAID records count as cash. Hours come
# from actual_hours (measured), never from estimates.
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ChannelEconomy:
    """Net-cash truth for one channel (platform)."""

    channel: str
    attempted: int = 0
    accepted: int = 0
    paid: int = 0
    earned_gross: float = 0.0
    net_cash: float = 0.0
    human_hours: float = 0.0
    net_per_hour: float | None = None
    median_days_to_cash: float | None = None
    acceptance_rate: float = 0.0
    cash_rate: float = 0.0


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[mid], 2)
    return round((ordered[mid - 1] + ordered[mid]) / 2.0, 2)


def channel_economy(records: list[LearningRecord]) -> dict:
    """Build the personal empirical economy table from verified outcomes.

    Honesty rules: no paid records -> verdict UNKNOWN (never $0-presented-as-fact
    for the rate table; totals stay 0.0). Hours only from actual_hours measured.
    """
    by_channel: dict[str, list[LearningRecord]] = defaultdict(list)
    for record in records:
        if record.platform:
            by_channel[record.platform].append(record)

    channels: list[dict] = []
    total_hours = 0.0
    total_net = 0.0
    for channel in sorted(by_channel):
        recs = by_channel[channel]
        accepted = [r for r in recs if r.accepted]
        paid = [r for r in recs if r.paid]
        earned_gross = round(sum(r.amount for r in accepted), 2)
        net_cash = round(sum(r.net_amount if r.net_amount is not None else 0.0 for r in paid), 2)
        hours = round(sum(r.actual_hours for r in recs if r.actual_hours is not None), 2)
        days = [r.time_to_payout_days for r in paid if r.time_to_payout_days is not None]
        total_hours += hours
        total_net += net_cash
        channels.append(
            {
                "channel": channel,
                "attempted": len(recs),
                "accepted": len(accepted),
                "paid": len(paid),
                "earned_gross": earned_gross,
                "net_cash": net_cash,
                "human_hours": hours,
                "net_per_hour": round(net_cash / hours, 2) if hours > 0 and net_cash > 0 else None,
                "median_days_to_cash": _median(days),
                "acceptance_rate": round(len(accepted) / len(recs), 3) if recs else 0.0,
                "cash_rate": round(len(paid) / len(recs), 3) if recs else 0.0,
            }
        )

    total_paid = sum(c["paid"] for c in channels)
    verdict = "UNKNOWN" if total_paid == 0 else ("THIN_EVIDENCE" if total_paid < 3 else "MEASURED")
    return {
        "verdict": verdict,
        "channels": channels,
        "totals": {
            "attempted": sum(c["attempted"] for c in channels),
            "accepted": sum(c["accepted"] for c in channels),
            "paid": total_paid,
            "earned_gross": round(sum(c["earned_gross"] for c in channels), 2),
            "net_cash": round(total_net, 2),
            "human_hours": round(total_hours, 2),
            "net_per_hour": round(total_net / total_hours, 2) if total_hours > 0 and total_net > 0 else None,
        },
        "note": (
            "Sin pagos verificados: no hay economía medible, solo escenarios."
            if verdict == "UNKNOWN"
            else f"Economía personal sobre {total_paid} pagos verificados."
        ),
    }


def prediction_error_report(records: list[LearningRecord]) -> dict:
    """Estimated-vs-actual calibration over records carrying prediction snapshots.

    Honesty rule: records without predictions are excluded and counted;
    with zero predicted records the verdict is UNKNOWN (never invented).
    """
    with_amount = [r for r in records if r.predicted_amount is not None]
    with_hours = [r for r in records if r.predicted_hours is not None and r.actual_hours is not None]
    with_prob = [r for r in records if r.predicted_probability is not None]

    def _mae(pairs: list[tuple[float, float]]) -> float | None:
        if not pairs:
            return None
        return round(sum(abs(a - p) for a, p in pairs) / len(pairs), 2)

    mae_amount = _mae([(r.amount, r.predicted_amount) for r in with_amount if r.predicted_amount is not None])
    mae_hours = _mae(
        [
            (r.actual_hours, r.predicted_hours)
            for r in with_hours
            if r.actual_hours is not None and r.predicted_hours is not None
        ]
    )
    mean_prob_error = None
    if with_prob:
        mean_prob_error = round(
            sum(abs((1.0 if r.accepted else 0.0) - float(r.predicted_probability or 0.0)) for r in with_prob)
            / len(with_prob),
            3,
        )

    if not with_amount and not with_hours and not with_prob:
        verdict = "UNKNOWN"
        note = "No hay predicciones registradas: imposible calibrar. Se necesitan predicted_amount/hours/probability en los outcomes."
    else:
        ids = {id(r) for r in with_amount + with_hours + with_prob}
        verdict = "CALIBRATED" if len(ids) >= 3 else "THIN_EVIDENCE"
        note = (
            f"Calibración sobre {len(with_amount)} montos, {len(with_hours)} tiempos, "
            f"{len(with_prob)} probabilidades ({len(ids)} outcomes)."
        )

    return {
        "verdict": verdict,
        "records_total": len(records),
        "records_with_amount_prediction": len(with_amount),
        "records_with_hours_prediction": len(with_hours),
        "records_with_probability_prediction": len(with_prob),
        "mae_amount_usd": mae_amount,
        "mae_hours": mae_hours,
        "mean_probability_error": mean_prob_error,
        "note": note,
    }


def identify_repeatable(
    records: list[LearningRecord],
    min_accepted: int = 2,
    min_conversion: float = 0.5,
    min_evidence: int = 3,
) -> list[dict]:
    """Identify repeatable income patterns from verified history.

    Verdicts: REPEATABLE (accepted >= min_accepted and conversion >=
    min_conversion), NON_REPEATABLE (enough evidence, below bar), UNKNOWN
    (insufficient evidence). RECURRING requires explicit subscription
    evidence, which history alone cannot prove — never claimed here.
    """
    by_key: dict[tuple[str, str], list[LearningRecord]] = defaultdict(list)
    for record in records:
        category = record.category.value if record.category else ""
        by_key[(record.platform, category)].append(record)

    out: list[dict] = []
    for (platform, category), items in sorted(by_key.items()):
        accepted = [r for r in items if r.accepted]
        total = len(items)
        conversion = round(len(accepted) / total, 3) if total else 0.0
        revenue = round(sum(r.amount for r in accepted), 2)
        if total < min_evidence:
            verdict = "UNKNOWN"
        elif len(accepted) >= min_accepted and conversion >= min_conversion:
            verdict = "REPEATABLE"
        else:
            verdict = "NON_REPEATABLE"
        out.append(
            {
                "platform": platform,
                "category": category,
                "accepted": len(accepted),
                "total": total,
                "conversion": conversion,
                "revenue_usd": revenue,
                "verdict": verdict,
            }
        )
    out.sort(key=lambda e: (-e["revenue_usd"], -e["conversion"]))
    return out


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
