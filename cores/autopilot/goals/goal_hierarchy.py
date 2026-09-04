"""Goal Hierarchy System - Multi-horizon objectives with auto-generated sprints."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GoalPeriod(StrEnum):
    LIFETIME = "lifetime"
    YEARLY = "yearly"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"
    SPRINT = "sprint"


class GoalStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"


@dataclass
class Goal:
    id: str
    name: str
    description: str
    period: GoalPeriod
    target_value: float
    current_value: float = 0.0
    unit: str = ""
    status: GoalStatus = GoalStatus.ACTIVE
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def progress_pct(self) -> float:
        if self.target_value == 0:
            return 0.0
        return min(100.0, (self.current_value / self.target_value) * 100)

    @property
    def is_completed(self) -> bool:
        return self.current_value >= self.target_value and self.status == GoalStatus.ACTIVE


@dataclass
class Sprint:
    id: str
    number: int
    name: str
    focus: str
    key_metric: str
    target: float
    start_date: datetime
    end_date: datetime
    goals: list[str] = field(default_factory=list)
    completed: bool = False


class GoalHierarchy:
    """
    Multi-horizon goal management with auto-generated sprints.

    Hierarchy:
    LIFETIME → YEARLY → QUARTERLY → MONTHLY → WEEKLY → DAILY → SPRINT

    Auto-generates sprints based on income targets and career progression.
    """

    def __init__(self, config: Any):
        self.config = config
        self._goals: dict[str, Goal] = {}
        self._sprints: list[Sprint] = []
        self._storage_path = Path.home() / ".ownex" / "goals.json"
        self._callbacks: list[Callable[[str, float], None]] = []

        # Initialize default hierarchy
        self._init_default_hierarchy()

    def _init_default_hierarchy(self) -> None:
        """Initialize default goal hierarchy from config."""
        targets = getattr(self.config, "income_targets", None)
        if not targets:
            return

        getattr(targets, "work_income_monthly_usd", 50000)
        getattr(targets, "savings_monthly_usd", 25000)
        getattr(targets, "capital_target_usd", 500000)
        getattr(targets, "target_monthly_usd", 100000)

        # Lifetime goal
        lifetime = Goal(
            id="lifetime_freedom",
            name="Libertad Financiera Total",
            description="Alcanzar $10M patrimonio neto para libertad financiera completa",
            period=GoalPeriod.LIFETIME,
            target_value=10_000_000,
            unit="USD",
        )

        # Yearly
        yearly = Goal(
            id="yearly_500k",
            name="Año 1: $500k Ahorrado + $1.2M Capital",
            description="Primer año: construir base sólida",
            period=GoalPeriod.YEARLY,
            target_value=500_000,
            unit="USD ahorrado",
            parent_id=lifetime.id,
        )
        lifetime.children.append(yearly.id)

        # Quarterly
        quarterly = Goal(
            id="quarterly_125k",
            name="Q1: $125k Ahorrado + $300k Capital",
            description="Primer trimestre: validación y tracción",
            period=GoalPeriod.QUARTERLY,
            target_value=125_000,
            unit="USD ahorrado",
            parent_id=yearly.id,
        )
        yearly.children.append(quarterly.id)

        # Monthly
        monthly = Goal(
            id="monthly_42k",
            name="Mes 1: $42k Ahorrado + $100k Capital",
            description="Primer mes: validación y primeras entregas",
            period=GoalPeriod.MONTHLY,
            target_value=42_000,
            unit="USD ahorrado",
            parent_id=quarterly.id,
        )
        quarterly.children.append(monthly.id)

        # Weekly
        weekly = Goal(
            id="weekly_10k",
            name="Semana 1: $10k Ahorrado + $25k Capital",
            description="Primera semana: onboarding y primeras entregas",
            period=GoalPeriod.WEEKLY,
            target_value=10_000,
            unit="USD ahorrado",
            parent_id=monthly.id,
        )
        monthly.children.append(weekly.id)

        # Daily
        daily = Goal(
            id="daily_1400",
            name="Hoy: $1,400 Ahorrado + $3,500 Capital",
            description="Objetivo diario de ahorro y capital",
            period=GoalPeriod.DAILY,
            target_value=1_400,
            unit="USD ahorrado",
            parent_id=weekly.id,
        )
        weekly.children.append(daily.id)

        # Daily sub-goals
        daily_income = Goal(
            id="daily_income_2800",
            name="Ingreso Diario Target: $2,800 EV",
            description="Objetivo de valor esperado diario",
            period=GoalPeriod.DAILY,
            target_value=2_800,
            unit="USD EV",
            parent_id=daily.id,
        )
        daily.children.append(daily_income.id)

        daily_workbank = Goal(
            id="daily_workbank_10",
            name="WorkBank: 10 Ready",
            description="10 items ready_to_deliver hoy",
            period=GoalPeriod.DAILY,
            target_value=10,
            unit="items",
            parent_id=daily.id,
        )
        daily.children.append(daily_workbank.id)

        daily_delivery = Goal(
            id="daily_delivery_5",
            name="Entregas: 5 Aprobadas",
            description="5 entregas aprobadas hoy",
            period=GoalPeriod.DAILY,
            target_value=5,
            unit="entregas",
            parent_id=daily.id,
        )
        daily.children.append(daily_delivery.id)

        daily_capital = Goal(
            id="daily_capital_3500",
            name="Capital: +$3,500 Neto",
            description="Incremento neto de capital hoy",
            period=GoalPeriod.DAILY,
            target_value=3_500,
            unit="USD",
            parent_id=daily.id,
        )
        daily.children.append(daily_capital.id)

        daily_learning = Goal(
            id="daily_learning_1",
            name="Learning: 1 Skill Gap Cerrado",
            description="Cerrar un gap de habilidad hoy",
            period=GoalPeriod.DAILY,
            target_value=1,
            unit="skills",
            parent_id=daily.id,
        )
        daily.children.append(daily_learning.id)

        # Register all goals
        all_goals = [
            lifetime,
            yearly,
            quarterly,
            monthly,
            weekly,
            daily,
            daily_income,
            daily_workbank,
            daily_delivery,
            daily_capital,
            daily_learning,
        ]

        for goal in all_goals:
            self._goals[goal.id] = goal

        # Auto-generate sprints
        self._generate_sprints()

    def _generate_sprints(self) -> None:
        """Auto-generate sprints based on career progression."""
        sprints = [
            Sprint(
                id="sprint_1",
                number=1,
                name="Onboarding + Base",
                focus="Configurar 8+ plataformas, validar payment rails",
                key_metric="Plataformas activas",
                target=8,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=14),
                goals=["first_platform", "keys_configured", "profile_complete"],
            ),
            Sprint(
                id="sprint_2",
                number=2,
                name="Cashflow Base",
                focus="Alcanzar $500 EV/día consistente",
                key_metric="$EV/día",
                target=500,
                start_date=datetime.utcnow() + timedelta(days=14),
                end_date=datetime.utcnow() + timedelta(days=28),
                goals=["first_100", "first_1k", "weekly_500"],
            ),
            Sprint(
                id="sprint_3",
                number=3,
                name="Security Entry",
                focus="10 findings válidos, primer private invite",
                key_metric="Findings válidos",
                target=10,
                start_date=datetime.utcnow() + timedelta(days=28),
                end_date=datetime.utcnow() + timedelta(days=42),
                goals=["first_valid", "private_invite"],
            ),
            Sprint(
                id="sprint_4",
                number=4,
                name="Dev Bounty Scale",
                focus="3 bounties $500+/semana consistentes",
                key_metric="$500+/semana",
                target=3,
                start_date=datetime.utcnow() + timedelta(days=42),
                end_date=datetime.utcnow() + timedelta(days=56),
                goals=["fifty_delivered", "hundred_ready"],
            ),
            Sprint(
                id="sprint_5",
                number=5,
                name="Specialist Tier",
                focus="Rate coding $35/hr en Outlier/Mercor",
                key_metric="Rate coding",
                target=35,
                start_date=datetime.utcnow() + timedelta(days=56),
                end_date=datetime.utcnow() + timedelta(days=70),
                goals=["first_10k", "specialist_tier"],
            ),
            Sprint(
                id="sprint_6",
                number=6,
                name="Team Hiring",
                focus="Hunter 1 onboard y productivo",
                key_metric="Hunter 1 output",
                target=3000,
                start_date=datetime.utcnow() + timedelta(days=70),
                end_date=datetime.utcnow() + timedelta(days=84),
                goals=["hunter_1", "team_10k"],
            ),
            Sprint(
                id="sprint_7",
                number=7,
                name="SaaS MVP",
                focus="5 pilotos pagando OWNEX Scout",
                key_metric="Pilotos pagando",
                target=5,
                start_date=datetime.utcnow() + timedelta(days=84),
                end_date=datetime.utcnow() + timedelta(days=98),
                goals=["saas_pilot", "saas_10k_mrr"],
            ),
        ]

        for sprint in sprints:
            self._sprints.append(sprint)

    async def initialize(self) -> None:
        """Load persisted goals."""
        await self._load()
        logger.info(f"GoalHierarchy initialized: {len(self._goals)} goals, {len(self._sprints)} sprints")

    def register_callback(self, callback: Callable[[str, float], None]) -> None:
        self._callbacks.append(callback)

    async def update_progress(self, goal_id: str | None = None) -> list[str]:
        """Update goal progress from system metrics. Returns completed goal IDs."""
        completed = []

        if goal_id:
            goals_to_check = [self._goals[goal_id]] if goal_id in self._goals else []
        else:
            goals_to_check = list(self._goals.values())

        for goal in goals_to_check:
            if goal.status != GoalStatus.ACTIVE:
                continue

            # Update from system metrics
            new_value = await self._fetch_metric(goal.id)
            if new_value is not None:
                goal.current_value = new_value
                goal.updated_at = datetime.utcnow()

                if goal.is_completed:
                    goal.status = GoalStatus.COMPLETED
                    goal.completed_at = datetime.utcnow()
                    completed.append(goal.id)

                    # Notify callbacks
                    for callback in self._callbacks:
                        try:
                            callback(goal.id, goal.current_value)
                        except Exception as e:
                            logger.error(f"Goal callback error: {e}")

        if completed:
            await self._save()

        return completed

    async def _fetch_metric(self, goal_id: str) -> float | None:
        """Fetch current metric value from system."""
        # This would integrate with actual system metrics
        # For now, return None - real implementation needs system integration
        return None

    def get_goal(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    def get_goals_by_period(self, period: GoalPeriod) -> list[Goal]:
        return [g for g in self._goals.values() if g.period == period]

    def get_active_goals(self) -> list[Goal]:
        return [g for g in self._goals.values() if g.status == GoalStatus.ACTIVE]

    def get_sprints(self) -> list[Sprint]:
        return self._sprints

    def get_current_sprint(self) -> Sprint | None:
        now = datetime.utcnow()
        for sprint in self._sprints:
            if sprint.start_date <= now <= sprint.end_date:
                return sprint
        return None

    def get_hierarchy_tree(self) -> dict[str, Any]:
        """Get full hierarchy as tree for frontend."""
        roots = [g for g in self._goals.values() if g.parent_id is None]

        def build_tree(goal: Goal) -> dict[str, Any]:
            return {
                "id": goal.id,
                "name": goal.name,
                "description": goal.description,
                "period": goal.period.value,
                "target": goal.target_value,
                "current": goal.current_value,
                "progress_pct": goal.progress_pct,
                "status": goal.status.value,
                "unit": goal.unit,
                "children": [build_tree(self._goals[cid]) for cid in goal.children if cid in self._goals],
            }

        return {
            "goals": [build_tree(r) for r in roots],
            "sprints": [
                {
                    "id": s.id,
                    "number": s.number,
                    "name": s.name,
                    "focus": s.focus,
                    "key_metric": s.key_metric,
                    "target": s.target,
                    "start_date": s.start_date.isoformat(),
                    "end_date": s.end_date.isoformat(),
                    "goals": s.goals,
                    "completed": s.completed,
                }
                for s in self._sprints
            ],
        }

    async def _save(self) -> None:
        storage_path = Path.home() / ".ownex" / "goals.json"
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "goals": {
                gid: {
                    "id": g.id,
                    "name": g.name,
                    "description": g.description,
                    "period": g.period.value,
                    "target_value": g.target_value,
                    "current_value": g.current_value,
                    "unit": g.unit,
                    "status": g.status.value,
                    "parent_id": g.parent_id,
                    "children": g.children,
                    "created_at": g.created_at.isoformat(),
                    "updated_at": g.updated_at.isoformat(),
                    "completed_at": g.completed_at.isoformat() if g.completed_at else None,
                    "metadata": g.metadata,
                }
                for gid, g in self._goals.items()
            },
            "sprints": [
                {
                    "id": s.id,
                    "number": s.number,
                    "name": s.name,
                    "focus": s.focus,
                    "key_metric": s.key_metric,
                    "target": s.target,
                    "start_date": s.start_date.isoformat(),
                    "end_date": s.end_date.isoformat(),
                    "goals": s.goals,
                    "completed": s.completed,
                }
                for s in self._sprints
            ],
        }

        storage_path = Path.home() / ".ownex" / "goals.json"
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_text(json.dumps(data, indent=2, default=str))

    async def _load(self) -> None:
        storage_path = Path.home() / ".ownex" / "goals.json"
        if not storage_path.exists():
            return

        try:
            data = json.loads(storage_path.read_text())

            for gid, gdata in data.get("goals", {}).items():
                if gid in self._goals:
                    g = self._goals[gid]
                    g.current_value = gdata.get("current_value", 0)
                    g.status = GoalStatus(gdata.get("status", "active"))
                    g.updated_at = (
                        datetime.fromisoformat(gdata["updated_at"]) if gdata.get("updated_at") else g.updated_at
                    )
                    if gdata.get("completed_at"):
                        g.completed_at = datetime.fromisoformat(gdata["completed_at"])

            logger.info("Loaded goals from storage")
        except Exception as e:
            logger.error(f"Failed to load goals: {e}")
