"""5-Pillar Orchestrator — Unifies all 5 zero-barrier income categories.

Pillar 1: Bug Bounty (HackerOne, Bugcrowd, Intigriti)
Pillar 2: AI Tasks (Outlier, Scale AI, Alignerr)
Pillar 3: Dev Bounty (Opire, Algora, IssueHunt)
Pillar 4: QA/Crowdtesting (Testlio, uTest, Testbirds)
Pillar 5: Data Annotation (Scale AI, Appen, Telus)

All pillars: $0 barrier, no portfolio, no interview, optimized profile only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.pillars.orchestrator")


@dataclass
class PillarSummary:
    """Summary of one income pillar."""

    name: str
    pillar_id: int
    platforms: list[str]
    avg_pay_rate: float
    pay_range: str
    barrier: str
    monthly_potential_low: float
    monthly_potential_high: float
    hours_per_day: float
    time_to_first_pay: str
    skill_requirements: list[str]
    portfolio_required: bool
    interview_required: bool
    repeatable: bool
    automation_potential: float  # 0-1

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "pillar_id": self.pillar_id,
            "platforms": self.platforms,
            "avg_pay_rate": self.avg_pay_rate,
            "pay_range": self.pay_range,
            "barrier": self.barrier,
            "monthly_potential": f"${self.monthly_potential_low:,.0f} - ${self.monthly_potential_high:,.0f}",
            "hours_per_day": self.hours_per_day,
            "time_to_first_pay": self.time_to_first_pay,
            "skill_requirements": self.skill_requirements,
            "portfolio_required": self.portfolio_required,
            "interview_required": self.interview_required,
            "repeatable": self.repeatable,
            "automation_potential": self.automation_potential,
        }


@dataclass
class FivePillarDashboard:
    """Complete 5-pillar dashboard."""

    pillars: list[PillarSummary]
    total_monthly_low: float
    total_monthly_high: float
    total_hours_per_day: float
    combined_ev_per_hour: float
    recommendations: list[str]
    next_best_pillar: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pillars": [p.to_dict() for p in self.pillars],
            "total_monthly_potential": f"${self.total_monthly_low:,.0f} - ${self.total_monthly_high:,.0f}",
            "total_hours_per_day": self.total_hours_per_day,
            "combined_ev_per_hour": f"${self.combined_ev_per_hour:.0f}",
            "recommendations": self.recommendations,
            "next_best_pillar": self.next_best_pillar,
            "timestamp": self.timestamp,
        }


class FivePillarOrchestrator:
    """Orchestrates all 5 zero-barrier income pillars."""

    def __init__(self) -> None:
        self.pillars = self._init_pillars()

    def _init_pillars(self) -> list[PillarSummary]:
        """Initialize the 5 pillars with real data."""
        return [
            PillarSummary(
                name="Bug Bounty",
                pillar_id=1,
                platforms=["HackerOne", "Bugcrowd", "Intigriti", "YesWeHack", "Immunefi", "Synack"],
                avg_pay_rate=75.0,
                pay_range="$200 - $50,000/bounty",
                barrier="$0",
                monthly_potential_low=2000,
                monthly_potential_high=20000,
                hours_per_day=1.5,
                time_to_first_pay="2-8 weeks",
                skill_requirements=["security", "api", "web", "reporting"],
                portfolio_required=False,
                interview_required=False,
                repeatable=True,
                automation_potential=0.75,
            ),
            PillarSummary(
                name="AI Tasks",
                pillar_id=2,
                platforms=["Outlier", "Scale AI", "Alignerr", "Mindrift", "Remotasks"],
                avg_pay_rate=24.0,
                pay_range="$12 - $45/hour",
                barrier="$0",
                monthly_potential_low=1000,
                monthly_potential_high=5000,
                hours_per_day=1.0,
                time_to_first_pay="1-2 weeks",
                skill_requirements=["reasoning", "ai", "attention_to_detail"],
                portfolio_required=False,
                interview_required=False,
                repeatable=True,
                automation_potential=0.3,
            ),
            PillarSummary(
                name="Dev Bounty",
                pillar_id=3,
                platforms=["Opire", "Algora", "IssueHunt", "Gitcoin", "Dework", "Open Collective"],
                avg_pay_rate=50.0,
                pay_range="$50 - $2,000/bounty",
                barrier="$0",
                monthly_potential_low=1000,
                monthly_potential_high=8000,
                hours_per_day=1.0,
                time_to_first_pay="1-4 weeks",
                skill_requirements=["python", "javascript", "git", "coding"],
                portfolio_required=False,
                interview_required=False,
                repeatable=True,
                automation_potential=0.5,
            ),
            PillarSummary(
                name="QA/Crowdtesting",
                pillar_id=4,
                platforms=["Testlio", "uTest", "Testbirds", "Bugcrowd Discovery"],
                avg_pay_rate=18.0,
                pay_range="$10 - $100/bug",
                barrier="$0",
                monthly_potential_low=500,
                monthly_potential_high=3000,
                hours_per_day=0.5,
                time_to_first_pay="1-2 weeks",
                skill_requirements=["attention_to_detail", "reporting", "qa"],
                portfolio_required=False,
                interview_required=False,
                repeatable=True,
                automation_potential=0.4,
            ),
            PillarSummary(
                name="Data Annotation",
                pillar_id=5,
                platforms=["Scale AI", "Outlier", "Appen", "Telus", "Clickworker"],
                avg_pay_rate=13.0,
                pay_range="$8 - $22/hour",
                barrier="$0",
                monthly_potential_low=500,
                monthly_potential_high=3000,
                hours_per_day=0.5,
                time_to_first_pay="1-2 weeks",
                skill_requirements=["attention_to_detail", "consistency", "patience"],
                portfolio_required=False,
                interview_required=False,
                repeatable=True,
                automation_potential=0.2,
            ),
        ]

    def get_dashboard(self) -> FivePillarDashboard:
        """Get complete 5-pillar dashboard."""
        total_low = sum(p.monthly_potential_low for p in self.pillars)
        total_high = sum(p.monthly_potential_high for p in self.pillars)
        total_hours = sum(p.hours_per_day for p in self.pillars)

        # Calculate combined EV/hour
        total_monthly_mid = (total_low + total_high) / 2
        total_monthly_hours = total_hours * 22  # working days
        combined_ev = total_monthly_mid / max(total_monthly_hours, 1)

        # Generate recommendations
        recommendations = self._generate_recommendations()

        # Determine next best pillar
        next_best = self._get_next_best_pillar()

        return FivePillarDashboard(
            pillars=self.pillars,
            total_monthly_low=total_low,
            total_monthly_high=total_high,
            total_hours_per_day=total_hours,
            combined_ev_per_hour=combined_ev,
            recommendations=recommendations,
            next_best_pillar=next_best,
            timestamp=datetime.now(UTC).isoformat(),
        )

    def _generate_recommendations(self) -> list[str]:
        """Generate actionable recommendations."""
        recs = []
        recs.append("Start with AI Tasks — fastest time to first pay (1-2 weeks)")
        recs.append("Set up Bug Bounty accounts — highest long-term potential")
        recs.append("Register on Dev Bounty platforms — builds portfolio while earning")
        recs.append(" diversify across 3+ pillars to reduce income risk")
        recs.append("Track HUMAN_MINUTES/DAY — optimize for max $/hour")
        return recs

    def _get_next_best_pillar(self) -> str:
        """Recommend the best pillar to start with."""
        # Priority: fastest time to first pay + highest EV/hour
        priorities = {
            "AI Tasks": 95,  # Fastest pay, good rate
            "QA/Crowdtesting": 85,  # Fast pay, easy start
            "Dev Bounty": 80,  # Good pay, builds skills
            "Data Annotation": 75,  # Stable, easy
            "Bug Bounty": 70,  # Highest ceiling, but slower start
        }
        best = max(priorities, key=priorities.get)
        return best

    def get_pillar(self, pillar_id: int) -> PillarSummary | None:
        """Get a specific pillar by ID."""
        for p in self.pillars:
            if p.pillar_id == pillar_id:
                return p
        return None

    def get_startup_plan(self) -> dict[str, Any]:
        """Get a day-by-day startup plan for the first week."""
        return {
            "day_1": {
                "focus": "AI Tasks + Data Annotation",
                "actions": [
                    "Register on Outlier.ai (10 min)",
                    "Register on Scale AI (10 min)",
                    "Pass qualification tests (1-2 hours)",
                    "Complete first tasks (1 hour)",
                ],
                "expected_income": "$0-30",
                "time_required": "2-3 hours",
            },
            "day_2": {
                "focus": "QA/Crowdtesting",
                "actions": [
                    "Register on uTest (10 min)",
                    "Register on Testlio (10 min)",
                    "Complete profiles (20 min)",
                    "Start first test cycle (1 hour)",
                ],
                "expected_income": "$10-30",
                "time_required": "2 hours",
            },
            "day_3": {
                "focus": "Dev Bounty",
                "actions": [
                    "Register on Opire (10 min)",
                    "Register on Algora (10 min)",
                    "Browse available bounties (30 min)",
                    "Start first bounty (1 hour)",
                ],
                "expected_income": "$0-50",
                "time_required": "2 hours",
            },
            "day_4": {
                "focus": "Bug Bounty",
                "actions": [
                    "Register on HackerOne (10 min)",
                    "Register on Bugcrowd (10 min)",
                    "Configure OWNEX with targets (30 min)",
                    "Start first recon (1 hour)",
                ],
                "expected_income": "$0",
                "time_required": "2 hours",
            },
            "day_5": {
                "focus": "Optimize & Diversify",
                "actions": [
                    "Review all platform accounts",
                    "Check qualification status",
                    "Continue best-performing pillar",
                    "Start second task in AI/Data",
                ],
                "expected_income": "$20-80",
                "time_required": "2-3 hours",
            },
            "day_6_7": {
                "focus": "Stabilize",
                "actions": [
                    "Establish daily routine",
                    "Set up OWNEX morning briefing",
                    "Track time vs income",
                    "Optimize EV/hour",
                ],
                "expected_income": "$50-150",
                "time_required": "2-3 hours/day",
            },
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize orchestrator state."""
        dashboard = self.get_dashboard()
        return {
            "dashboard": dashboard.to_dict(),
            "startup_plan": self.get_startup_plan(),
        }


# Singleton
_five_pillar_orchestrator: FivePillarOrchestrator | None = None


def get_five_pillar_orchestrator() -> FivePillarOrchestrator:
    """Get or create the global 5-pillar orchestrator."""
    global _five_pillar_orchestrator
    if _five_pillar_orchestrator is None:
        _five_pillar_orchestrator = FivePillarOrchestrator()
    return _five_pillar_orchestrator
