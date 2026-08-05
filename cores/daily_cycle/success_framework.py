"""
OWNEX Success Framework — Maximum success daily, weekly, monthly, yearly.

Integrates with: Daily Cycle, Opportunity Engine, Income Dashboard, Memory, Learning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from cores.daily_cycle.system import get_daily_engine
from cores.direct_work_engine.income_dashboard import get_income_dashboard
from cores.memory.system import MemoryNamespace, MemoryTier, get_memory_store
from cores.opportunity.engine import get_opportunity_engine


class TimeHorizon(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class SuccessMetric:
    name: str
    target: float
    current: float = 0.0
    unit: str = ""
    critical: bool = True

    @property
    def achievement_pct(self) -> float:
        if self.target == 0:
            return 100.0
        return min((self.current / self.target) * 100, 100.0)

    @property
    def status(self) -> str:
        pct = self.achievement_pct
        if pct >= 100:
            return "✅ ACHIEVED"
        elif pct >= 80:
            return "🟢 ON TRACK"
        elif pct >= 50:
            return "🟡 BEHIND"
        else:
            return "🔴 CRITICAL"


@dataclass
class TimeHorizonTargets:
    horizon: TimeHorizon
    metrics: list[SuccessMetric] = field(default_factory=list)
    focus_areas: list[str] = field(default_factory=list)
    review_questions: list[str] = field(default_factory=list)


class SuccessFramework:
    """OWNEX Success Framework — Multi-horizon target tracking."""

    def __init__(self):
        self.memory = get_memory_store()
        self.daily_engine = get_daily_engine()
        self.opportunity_engine = get_opportunity_engine()
        self.income_dashboard = get_income_dashboard()

    # ============================================================
    # TARGET DEFINITIONS
    # ============================================================

    def get_daily_targets(self) -> TimeHorizonTargets:
        return TimeHorizonTargets(
            horizon=TimeHorizon.DAILY,
            metrics=[
                SuccessMetric("opportunities_analyzed", 20, unit="ops", critical=True),
                SuccessMetric("opportunities_passed_filter", 5, unit="ops", critical=True),
                SuccessMetric("top_opportunities_selected", 3, unit="ops", critical=True),
                SuccessMetric("hours_automated_via_ownex", 2, unit="hrs", critical=True),
                SuccessMetric("income_generated_today", 50, unit="USD", critical=False),
                SuccessMetric("tasks_completed", 5, unit="tasks", critical=True),
                SuccessMetric("learning_minutes", 30, unit="min", critical=False),
                SuccessMetric("health_score", 85, unit="score", critical=True),
            ],
            focus_areas=[
                "Morning pipeline execution",
                "Top 3 opportunity execution",
                "Automation of repetitive tasks",
                "Real-time decision making",
            ],
            review_questions=[
                "What was the highest EV opportunity today?",
                "What did OWNEX automate that saved time?",
                "What decision had the highest impact?",
                "What should be automated tomorrow?",
            ],
        )

    def get_weekly_targets(self) -> TimeHorizonTargets:
        return TimeHorizonTargets(
            horizon=TimeHorizon.WEEKLY,
            metrics=[
                SuccessMetric("total_income", 500, unit="USD", critical=True),
                SuccessMetric("opportunities_delivered", 10, unit="ops", critical=True),
                SuccessMetric("new_sources_explored", 2, unit="sources", critical=False),
                SuccessMetric("automation_pct_improved", 5, unit="%", critical=True),
                SuccessMetric("skills_acquired", 1, unit="skill", critical=False),
                SuccessMetric("pipeline_efficiency", 80, unit="%", critical=True),
                SuccessMetric("health_score_avg", 90, unit="score", critical=True),
            ],
            focus_areas=[
                "Portfolio diversification across categories",
                "Automation compound effects",
                "Source quality improvement",
                "Skill gap closure",
            ],
            review_questions=[
                "Which category generated highest ROI?",
                "What automation had the biggest time savings?",
                "Which source is underperforming?",
                "What new skill would unlock next level?",
            ],
        )

    def get_monthly_targets(self) -> TimeHorizonTargets:
        return TimeHorizonTargets(
            horizon=TimeHorizon.MONTHLY,
            metrics=[
                SuccessMetric("total_income", 2500, unit="USD", critical=True),
                SuccessMetric("opportunities_delivered", 40, unit="ops", critical=True),
                SuccessMetric("new_categories_entered", 1, unit="cat", critical=False),
                SuccessMetric("automation_coverage", 60, unit="%", critical=True),
                SuccessMetric("passive_income_pct", 20, unit="%", critical=False),
                SuccessMetric("new_sources_activated", 3, unit="sources", critical=True),
                SuccessMetric("skill_mastery_advanced", 1, unit="skill", critical=False),
            ],
            focus_areas=[
                "Scale winning categories",
                "Build automation moats",
                "Enter new high-EV categories",
                "Compound passive income",
            ],
            review_questions=[
                "Which 20% of activities generated 80% of income?",
                "What new category should we enter next month?",
                "What automation ROI was highest?",
                "What's the bottleneck to 2x income?",
            ],
        )

    def get_yearly_targets(self) -> TimeHorizonTargets:
        return TimeHorizonTargets(
            horizon=TimeHorizon.YEARLY,
            metrics=[
                SuccessMetric("total_income", 100000, unit="USD", critical=True),
                SuccessMetric("opportunities_delivered", 500, unit="ops", critical=True),
                SuccessMetric("categories_mastered", 5, unit="cat", critical=True),
                SuccessMetric("automation_coverage", 85, unit="%", critical=True),
                SuccessMetric("passive_income", 30000, unit="USD", critical=True),
                SuccessMetric("sources_mastered", 20, unit="sources", critical=True),
                SuccessMetric("compound_skills", 10, unit="skills", critical=True),
                SuccessMetric("net_worth_increase", 50000, unit="USD", critical=False),
            ],
            focus_areas=[
                "Financial independence via compound automation",
                "Category leadership in top 3 niches",
                "Passive income exceeds active income",
                "OWNEX becomes self-improving system",
            ],
            review_questions=[
                "Did we achieve financial independence?",
                "Is OWNEX self-improving without manual intervention?",
                "What's the next 10x opportunity?",
                "What would we do differently knowing what we know now?",
            ],
        )

    # ============================================================
    # TRACKING & PERSISTENCE
    # ============================================================

    def save_targets(self, horizon: TimeHorizon, targets: TimeHorizonTargets) -> None:
        key = f"success_targets_{horizon.value}"
        self.memory.set(
            MemoryNamespace.SYSTEM_HEALTH,
            key,
            {
                "horizon": horizon.value,
                "metrics": [
                    {
                        "name": m.name,
                        "target": m.target,
                        "unit": m.unit,
                        "critical": m.critical,
                    }
                    for m in targets.metrics
                ],
                "focus_areas": targets.focus_areas,
                "review_questions": targets.review_questions,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            tier=MemoryTier.PERMANENT,
            tags=["success_framework", "targets"],
        )

    def load_targets(self, horizon: TimeHorizon) -> TimeHorizonTargets | None:
        key = f"success_targets_{horizon.value}"
        data = self.memory.get(MemoryNamespace.SYSTEM_HEALTH, key)
        if not data:
            return None

        targets = self._get_targets_for_horizon(horizon)
        # Update with saved current values if available
        if "current_values" in data:
            for _i, metric in enumerate(targets.metrics):
                if metric.name in data["current_values"]:
                    metric.current = data["current_values"][metric.name]
        return targets

    def _get_targets_for_horizon(self, horizon: TimeHorizon) -> TimeHorizonTargets:
        if horizon == TimeHorizon.DAILY:
            return self.get_daily_targets()
        elif horizon == TimeHorizon.WEEKLY:
            return self.get_weekly_targets()
        elif horizon == TimeHorizon.MONTHLY:
            return self.get_monthly_targets()
        elif horizon == TimeHorizon.YEARLY:
            return self.get_yearly_targets()
        raise ValueError(f"Unknown horizon: {horizon}")

    def update_current(self, horizon: TimeHorizon, metric_name: str, value: float) -> None:
        key = f"success_targets_{horizon.value}"
        data = self.memory.get(MemoryNamespace.SYSTEM_HEALTH, key) or {}
        if "current_values" not in data:
            data["current_values"] = {}
        data["current_values"][metric_name] = value
        data["last_updated"] = datetime.now(UTC).isoformat()
        self.memory.set(
            MemoryNamespace.SYSTEM_HEALTH,
            key,
            data,
            tier=MemoryTier.PERMANENT,
            tags=["success_framework", "current_values"],
        )

    # ============================================================
    # REPORTING
    # ============================================================

    def get_dashboard(self) -> dict[str, Any]:
        """Unified success dashboard across all horizons."""
        horizons = [
            TimeHorizon.DAILY,
            TimeHorizon.WEEKLY,
            TimeHorizon.MONTHLY,
            TimeHorizon.YEARLY,
        ]

        dashboard = {
            "generated_at": datetime.now(UTC).isoformat(),
            "horizons": {},
        }

        for h in horizons:
            targets = self._get_targets_for_horizon(h)
            metrics_data = []
            for m in targets.metrics:
                metrics_data.append(
                    {
                        "name": m.name,
                        "target": m.target,
                        "current": m.current,
                        "unit": m.unit,
                        "achievement_pct": m.achievement_pct,
                        "status": m.status,
                        "critical": m.critical,
                    }
                )

            critical_metrics = [m for m in targets.metrics if m.critical]
            critical_avg = (
                sum(m.achievement_pct for m in critical_metrics) / len(critical_metrics) if critical_metrics else 0
            )

            dashboard["horizons"][h.value] = {
                "metrics": metrics_data,
                "focus_areas": targets.focus_areas,
                "review_questions": targets.review_questions,
                "critical_health": critical_avg,
                "overall_status": "🟢 HEALTHY"
                if critical_avg >= 80
                else "🟡 ATTENTION"
                if critical_avg >= 50
                else "🔴 CRITICAL",
            }

        # Overall health
        all_critical = []
        for h in horizons:
            targets = self._get_targets_for_horizon(h)
            all_critical.extend([m for m in targets.metrics if m.critical])

        overall_health = sum(m.achievement_pct for m in all_critical) / len(all_critical) if all_critical else 0
        dashboard["overall_health"] = overall_health
        dashboard["overall_status"] = (
            "🟢 EXCELLENT"
            if overall_health >= 90
            else "🟢 GOOD"
            if overall_health >= 80
            else "🟡 MODERATE"
            if overall_health >= 60
            else "🟠 CONCERNING"
            if overall_health >= 40
            else "🔴 CRITICAL"
        )

        return dashboard

    def generate_review(self, horizon: TimeHorizon) -> str:
        """Generate review report for a time horizon."""
        targets = self._get_targets_for_horizon(horizon)

        lines = [
            f"📊 **OWNEX {horizon.value.upper()} REVIEW**",
            f"📅 {datetime.now(UTC).strftime('%Y-%m-%d')}",
            "",
        ]

        for m in targets.metrics:
            status_emoji = (
                "✅"
                if m.achievement_pct >= 100
                else "🟢"
                if m.achievement_pct >= 80
                else "🟡"
                if m.achievement_pct >= 50
                else "🔴"
            )
            lines.append(f"{status_emoji} **{m.name}**: {m.current:.1f}/{m.target} {m.unit} ({m.achievement_pct:.0f}%)")

        lines.extend(
            [
                "",
                "🎯 **Focus Areas:**",
            ]
        )
        for area in targets.focus_areas:
            lines.append(f"  • {area}")

        lines.extend(
            [
                "",
                "❓ **Review Questions:**",
            ]
        )
        for q in targets.review_questions:
            lines.append(f"  • {q}")

        return "\n".join(lines)

    def run_daily_success_check(self) -> dict[str, Any]:
        """Run daily success metrics collection from live systems."""
        # Get real data from systems
        daily_briefing = self.daily_engine.generate_briefing()
        income_snapshot = self.income_dashboard.snapshot()

        # Update metrics with real data
        self.update_current(
            TimeHorizon.DAILY, "opportunities_analyzed", getattr(daily_briefing, "opportunities_analyzed", 0)
        )
        self.update_current(
            TimeHorizon.DAILY, "opportunities_passed_filter", getattr(daily_briefing, "opportunities_passed_filter", 0)
        )
        self.update_current(
            TimeHorizon.DAILY, "top_opportunities_selected", len(getattr(daily_briefing, "top_opportunities", []))
        )
        self.update_current(
            TimeHorizon.DAILY, "income_generated_today", income_snapshot.get("income", {}).get("total_earned_usd", 0)
        )
        self.update_current(TimeHorizon.DAILY, "health_score", getattr(daily_briefing, "system", {}).get("score", 0))

        return self.get_dashboard()


# ============================================================
# GLOBAL INSTANCE
# ============================================================

_success_framework: SuccessFramework | None = None


def get_success_framework() -> SuccessFramework:
    global _success_framework
    if _success_framework is None:
        _success_framework = SuccessFramework()
        # Initialize all targets
        for h in [TimeHorizon.DAILY, TimeHorizon.WEEKLY, TimeHorizon.MONTHLY, TimeHorizon.YEARLY]:
            targets = _success_framework._get_targets_for_horizon(h)
            _success_framework.save_targets(h, targets)
    return _success_framework


async def run_success_check() -> dict[str, Any]:
    """Run daily success check and return dashboard."""
    framework = get_success_framework()
    return framework.run_daily_success_check()


async def get_success_dashboard() -> dict[str, Any]:
    framework = get_success_framework()
    return framework.get_dashboard()


async def get_review(horizon: TimeHorizon) -> str:
    framework = get_success_framework()
    return framework.generate_review(horizon)
