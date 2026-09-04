"""$1M Capital Engine — Projection, compound interest, goals, and scenarios.

Core engine for tracking progress toward $1M net worth.
Calculates: current capital, remaining, savings rate, projected date,
required monthly contribution, and scenarios (conservative/base/aggressive).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.capital.engine")


@dataclass
class FinancialGoal:
    """A financial goal (auto, vivienda, reserva, $1M)."""

    id: str
    name: str
    target_amount: float
    current_amount: float = 0.0
    monthly_contribution: float = 0.0
    priority: int = 1  # 1=highest
    category: str = "general"  # auto, vivienda, reserva, capital, million
    deadline_months: int | None = None  # months to reach goal
    notes: str = ""

    @property
    def progress_pct(self) -> float:
        if self.target_amount <= 0:
            return 0.0
        return min((self.current_amount / self.target_amount) * 100, 100.0)

    @property
    def remaining(self) -> float:
        return max(self.target_amount - self.current_amount, 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "target_amount": self.target_amount,
            "current_amount": self.current_amount,
            "monthly_contribution": self.monthly_contribution,
            "priority": self.priority,
            "category": self.category,
            "deadline_months": self.deadline_months,
            "progress_pct": round(self.progress_pct, 2),
            "remaining": round(self.remaining, 2),
            "notes": self.notes,
        }


@dataclass
class ProjectionScenario:
    """A projection scenario (conservative/base/aggressive/exceptional)."""

    name: str
    monthly_income: float
    monthly_savings_rate: float  # 0.0 to 1.0
    monthly_investment_return: float  # monthly return rate (e.g., 0.005 = 0.5%/month)
    initial_capital: float = 0.0

    def project(self, months: int = 120) -> list[dict[str, Any]]:
        """Project capital growth over N months with compound interest."""
        capital = self.initial_capital
        monthly_savings = self.monthly_income * self.monthly_savings_rate
        projections = []

        for month in range(1, months + 1):
            # Compound interest on existing capital
            capital += capital * self.monthly_investment_return
            # Add monthly savings
            capital += monthly_savings

            projections.append(
                {
                    "month": month,
                    "capital": round(capital, 2),
                    "monthly_savings": round(monthly_savings, 2),
                    "cumulative_contributions": round(self.initial_capital + monthly_savings * month, 2),
                    "cumulative_growth": round(capital - self.initial_capital - monthly_savings * month, 2),
                }
            )

        return projections

    def months_to_reach(self, target: float) -> int | None:
        """Calculate months to reach target amount."""
        capital = self.initial_capital
        monthly_savings = self.monthly_income * self.monthly_savings_rate

        if capital >= target:
            return 0

        if monthly_savings <= 0 and self.monthly_investment_return <= 0:
            return None  # Never reach target

        for month in range(1, 1201):  # Max 100 years
            capital += capital * self.monthly_investment_return
            capital += monthly_savings
            if capital >= target:
                return month

        return None  # Beyond 100 years


@dataclass
class CapitalState:
    """Current capital state."""

    net_worth: float = 0.0
    cash: float = 0.0
    savings: float = 0.0
    investments: float = 0.0
    monthly_income: float = 0.0
    monthly_expenses: float = 0.0
    monthly_savings: float = 0.0
    savings_rate: float = 0.0
    runway_months: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "net_worth": round(self.net_worth, 2),
            "cash": round(self.cash, 2),
            "savings": round(self.savings, 2),
            "investments": round(self.investments, 2),
            "monthly_income": round(self.monthly_income, 2),
            "monthly_expenses": round(self.monthly_expenses, 2),
            "monthly_savings": round(self.monthly_savings, 2),
            "savings_rate": round(self.savings_rate * 100, 2),
            "runway_months": round(self.runway_months, 1),
        }


class CapitalEngine:
    """$1M Capital Engine — projections, compound interest, goals, scenarios."""

    MILLION_TARGET = 1_000_000.0

    def __init__(self) -> None:
        self.goals: list[FinancialGoal] = []
        self.state = CapitalState()
        self.scenarios: dict[str, ProjectionScenario] = {}
        self._init_default_scenarios()
        self._init_default_goals()

    def _persist_state(self) -> None:
        """Persist state and goals to DB."""
        try:
            from database.persistence import get_capital_persistence

            persist = get_capital_persistence()
            persist.save_state(self.state)
            persist.save_goals(self.goals)
        except Exception:
            pass  # Best effort

    def _load_from_db(self) -> None:
        """Load state and goals from DB."""
        try:
            from database.persistence import get_capital_persistence

            persist = get_capital_persistence()
            state_data = persist.load_state()
            if state_data:
                self.update_state(**state_data)
            goals_data = persist.load_goals()
            if goals_data:
                self.goals = [
                    FinancialGoal(
                        id=g["id"],
                        name=g["name"],
                        target_amount=g["target_amount"],
                        current_amount=g["current_amount"],
                        monthly_contribution=g["monthly_contribution"],
                        priority=g["priority"],
                        category=g["category"],
                        deadline_months=g.get("deadline_months"),
                        notes=g.get("notes", ""),
                    )
                    for g in goals_data
                ]
        except Exception:
            pass  # Use defaults

    def _init_default_scenarios(self) -> None:
        """Initialize default projection scenarios."""
        self.scenarios = {
            "conservative": ProjectionScenario(
                name="Conservative",
                monthly_income=self.state.monthly_income or 2000,
                monthly_savings_rate=0.20,
                monthly_investment_return=0.004,  # ~5% annual
                initial_capital=self.state.net_worth,
            ),
            "base": ProjectionScenario(
                name="Base",
                monthly_income=self.state.monthly_income or 3000,
                monthly_savings_rate=0.30,
                monthly_investment_return=0.006,  # ~7.5% annual
                initial_capital=self.state.net_worth,
            ),
            "aggressive": ProjectionScenario(
                name="Aggressive",
                monthly_income=self.state.monthly_income or 5000,
                monthly_savings_rate=0.40,
                monthly_investment_return=0.008,  # ~10% annual
                initial_capital=self.state.net_worth,
            ),
            "exceptional": ProjectionScenario(
                name="Exceptional",
                monthly_income=self.state.monthly_income or 10000,
                monthly_savings_rate=0.50,
                monthly_investment_return=0.010,  # ~12.7% annual
                initial_capital=self.state.net_worth,
            ),
        }

    def _init_default_goals(self) -> None:
        """Initialize default financial goals."""
        self.goals = [
            FinancialGoal(
                id="emergency_fund",
                name="Emergency Fund",
                target_amount=10_000,
                category="reserva",
                priority=1,
                notes="6 months of expenses",
            ),
            FinancialGoal(
                id="car",
                name="Car (Economic)",
                target_amount=15_000,
                category="auto",
                priority=2,
                notes="Economic vehicle + insurance + transfer",
            ),
            FinancialGoal(
                id="apartment_buenos_aires",
                name="Apartment Buenos Aires",
                target_amount=80_000,
                category="vivienda",
                priority=3,
                notes="Departamento amueblado con cochera",
            ),
            FinancialGoal(
                id="million",
                name="$1M Net Worth",
                target_amount=self.MILLION_TARGET,
                category="million",
                priority=4,
                notes="Ultimate wealth goal",
            ),
        ]

    def update_state(
        self,
        net_worth: float | None = None,
        cash: float | None = None,
        savings: float | None = None,
        investments: float | None = None,
        monthly_income: float | None = None,
        monthly_expenses: float | None = None,
    ) -> None:
        """Update capital state."""
        if net_worth is not None:
            self.state.net_worth = net_worth
        if cash is not None:
            self.state.cash = cash
        if savings is not None:
            self.state.savings = savings
        if investments is not None:
            self.state.investments = investments
        if monthly_income is not None:
            self.state.monthly_income = monthly_income
        if monthly_expenses is not None:
            self.state.monthly_expenses = monthly_expenses

        # Calculate derived fields
        self.state.monthly_savings = self.state.monthly_income - self.state.monthly_expenses
        if self.state.monthly_income > 0:
            self.state.savings_rate = self.state.monthly_savings / self.state.monthly_income
        else:
            self.state.savings_rate = 0.0

        if self.state.monthly_expenses > 0:
            self.state.runway_months = self.state.cash / self.state.monthly_expenses
        else:
            self.state.runway_months = float("inf")

        # Update scenario initial capital
        for scenario in self.scenarios.values():
            scenario.initial_capital = self.state.net_worth
            scenario.monthly_income = self.state.monthly_income

        # Persist to DB
        self._persist_state()

    def add_goal(
        self,
        name: str,
        target_amount: float,
        category: str = "general",
        priority: int = 5,
        monthly_contribution: float = 0.0,
        notes: str = "",
    ) -> FinancialGoal:
        """Add a new financial goal."""
        goal_id = name.lower().replace(" ", "_")
        goal = FinancialGoal(
            id=goal_id,
            name=name,
            target_amount=target_amount,
            category=category,
            priority=priority,
            monthly_contribution=monthly_contribution,
            notes=notes,
        )
        self.goals.append(goal)
        return goal

    def update_goal(
        self,
        goal_id: str,
        current_amount: float | None = None,
        monthly_contribution: float | None = None,
    ) -> FinancialGoal | None:
        """Update a financial goal."""
        for goal in self.goals:
            if goal.id == goal_id:
                if current_amount is not None:
                    goal.current_amount = current_amount
                if monthly_contribution is not None:
                    goal.monthly_contribution = monthly_contribution
                return goal
        return None

    def get_goal_projections(self, goal_id: str, months: int = 120) -> dict[str, Any]:
        """Get projection for a specific goal."""
        goal = next((g for g in self.goals if g.id == goal_id), None)
        if not goal:
            return {"error": f"Goal {goal_id} not found"}

        # Project using base scenario
        scenario = self.scenarios.get("base")
        if not scenario:
            return {"error": "No base scenario"}

        # Create projection for this goal
        capital = goal.current_amount
        monthly = goal.monthly_contribution or (self.state.monthly_savings * 0.3)
        return_rate = scenario.monthly_investment_return

        projections = []
        for month in range(1, months + 1):
            capital += capital * return_rate
            capital += monthly
            projections.append(
                {
                    "month": month,
                    "amount": round(capital, 2),
                }
            )
            if capital >= goal.target_amount:
                break

        # Find months to reach goal
        months_to_goal = None
        for p in projections:
            if p["amount"] >= goal.target_amount:
                months_to_goal = p["month"]
                break

        return {
            "goal": goal.to_dict(),
            "months_to_reach": months_to_goal,
            "projections": projections[:12],  # First 12 months
        }

    def get_all_projections(self) -> dict[str, Any]:
        """Get projections for all scenarios."""
        projections = {}
        for name, scenario in self.scenarios.items():
            proj = scenario.project(months=120)
            months_to_million = scenario.months_to_reach(self.MILLION_TARGET)
            projections[name] = {
                "name": scenario.name,
                "monthly_income": scenario.monthly_income,
                "savings_rate": scenario.monthly_savings_rate,
                "return_rate": scenario.monthly_investment_return,
                "months_to_million": months_to_million,
                "projected_date": (
                    datetime.now(UTC)
                    .replace(
                        month=((datetime.now(UTC).month - 1 + months_to_million) % 12) + 1,
                        year=datetime.now(UTC).year + ((datetime.now(UTC).month - 1 + months_to_million) // 12),
                    )
                    .strftime("%Y-%m")
                    if months_to_million
                    else "Never"
                ),
                "first_12_months": proj[:12],
            }
        return projections

    def get_dashboard(self) -> dict[str, Any]:
        """Get complete capital dashboard."""
        projections = self.get_all_projections()

        # Calculate gap to $1M
        gap = self.MILLION_TARGET - self.state.net_worth
        progress_to_million = (self.state.net_worth / self.MILLION_TARGET) * 100

        # Required monthly for each scenario to reach $1M in 5 years (60 months)
        required_monthly = {}
        for name, scenario in self.scenarios.items():
            # Solve for monthly contribution needed
            months = 60
            r = scenario.monthly_investment_return
            if r > 0:
                # FV = PV*(1+r)^n + PMT*((1+r)^n - 1)/r
                # PMT = (FV - PV*(1+r)^n) * r / ((1+r)^n - 1)
                factor = (1 + r) ** months
                if factor > 1:
                    pmt = (self.MILLION_TARGET - self.state.net_worth * factor) * r / (factor - 1)
                    required_monthly[name] = max(round(pmt, 2), 0)
                else:
                    required_monthly[name] = 0
            else:
                required_monthly[name] = round(gap / months, 2) if months > 0 else 0

        return {
            "state": self.state.to_dict(),
            "million_target": self.MILLION_TARGET,
            "gap_to_million": round(gap, 2),
            "progress_to_million": round(progress_to_million, 2),
            "goals": [g.to_dict() for g in self.goals],
            "projections": projections,
            "required_monthly_5yr": required_monthly,
            "updated_at": datetime.now(UTC).isoformat(),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize engine state."""
        return self.get_dashboard()


# Singleton
_capital_engine: CapitalEngine | None = None


def get_capital_engine() -> CapitalEngine:
    """Get or create the global capital engine."""
    global _capital_engine
    if _capital_engine is None:
        _capital_engine = CapitalEngine()
    return _capital_engine
