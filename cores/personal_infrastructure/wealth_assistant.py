"""Wealth & Finance Assistant - Assistant Financiero.

Gestiona seguimiento de ingresos, organización financiera, análisis, reportes,
preparación fiscal y planificación.

REGLA DE ORO: Nunca almacenar contraseñas bancarias, claves privadas o credenciales sensibles.
Usar OAuth, APIs oficiales, conexiones seguras y archivos exportados por usuario.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from cores.personal_infrastructure.models import WealthAccount

logger = logging.getLogger("ownex.personal_infrastructure.wealth_assistant")

WEALTH_DATA_PATH = Path.home() / ".ownex" / "personal_infrastructure" / "wealth"
INCOME_FILE = WEALTH_DATA_PATH / "income.json"
EXPENSES_FILE = WEALTH_DATA_PATH / "expenses.json"
GOALS_FILE = WEALTH_DATA_PATH / "goals.json"
RECOMMENDATIONS_FILE = WEALTH_DATA_PATH / "recommendations.json"


class IncomeSource(StrEnum):
    """Fuentes de ingresos."""
    BUG_BOUNTY = "bug_bounty"
    DEV_BOUNTY = "dev_bounty"
    FREELANCE = "freelance"
    SALARY = "salary"
    INVESTMENT = "investment"
    OTHER = "other"


class ExpenseCategory(StrEnum):
    """Categorías de gastos."""
    TOOLS = "tools"  # Software, servicios
    HARDWARE = "hardware"  # Hardware, equipos
    EDUCATION = "education"  # Cursos, libros
    SUBSCRIPTIONS = "subscriptions"  # Suscripciones mensuales
    LIVING = "living"  # Gastos de vida
    TAXES = "taxes"  # Impuestos
    OTHER = "other"


@dataclass
class IncomeEntry:
    """Entrada de ingreso."""
    entry_id: str
    source: IncomeSource
    amount: Decimal
    currency: str
    date: datetime
    platform: str  # HackerOne, Upwork, etc.
    description: str
    account_id: str  # ID de cuenta de WealthAccount (sin datos sensibles)
    status: str = "pending"  # pending, received, withdrawn


@dataclass
class ExpenseEntry:
    """Entrada de gasto."""
    entry_id: str
    category: ExpenseCategory
    amount: Decimal
    currency: str
    date: datetime
    description: str
    is_deductible: bool = False  # ¿Es deducible fiscalmente?


@dataclass
class FinancialGoal:
    """Meta financiera."""
    goal_id: str
    title: str
    target_amount: Decimal
    current_amount: Decimal
    currency: str
    deadline: datetime
    category: str  # savings, investment, equipment, education
    status: str = "in_progress"


@dataclass
class FinancialRecommendation:
    """Recomendación financiera."""
    recommendation_id: str
    title: str
    description: str
    priority: str  # high, medium, low
    estimated_impact: str
    action_required: str
    created_at: datetime


class WealthAssistant:
    """Asistente financiero personal."""

    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or WEALTH_DATA_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.income: dict[str, IncomeEntry] = {}
        self.expenses: dict[str, ExpenseEntry] = {}
        self.goals: dict[str, FinancialGoal] = {}
        self.recommendations: dict[str, FinancialRecommendation] = {}

        self._load_data()

    def _load_data(self) -> None:
        """Cargar datos financieros."""
        try:
            if INCOME_FILE.exists():
                with open(INCOME_FILE) as f:
                    data = json.load(f)
                    for entry_id, entry_data in data.items():
                        if entry_data.get("source"):
                            entry_data["source"] = IncomeSource(entry_data["source"])
                        if entry_data.get("date"):
                            entry_data["date"] = datetime.fromisoformat(entry_data["date"])
                        if entry_data.get("amount"):
                            entry_data["amount"] = Decimal(str(entry_data["amount"]))
                        self.income[entry_id] = IncomeEntry(**entry_data)

            if EXPENSES_FILE.exists():
                with open(EXPENSES_FILE) as f:
                    data = json.load(f)
                    for entry_id, entry_data in data.items():
                        if entry_data.get("category"):
                            entry_data["category"] = ExpenseCategory(entry_data["category"])
                        if entry_data.get("date"):
                            entry_data["date"] = datetime.fromisoformat(entry_data["date"])
                        if entry_data.get("amount"):
                            entry_data["amount"] = Decimal(str(entry_data["amount"]))
                        self.expenses[entry_id] = ExpenseEntry(**entry_data)

            if GOALS_FILE.exists():
                with open(GOALS_FILE) as f:
                    data = json.load(f)
                    for goal_id, goal_data in data.items():
                        if goal_data.get("deadline"):
                            goal_data["deadline"] = datetime.fromisoformat(goal_data["deadline"])
                        if goal_data.get("target_amount"):
                            goal_data["target_amount"] = Decimal(str(goal_data["target_amount"]))
                        if goal_data.get("current_amount"):
                            goal_data["current_amount"] = Decimal(str(goal_data["current_amount"]))
                        self.goals[goal_id] = FinancialGoal(**goal_data)

            if RECOMMENDATIONS_FILE.exists():
                with open(RECOMMENDATIONS_FILE) as f:
                    data = json.load(f)
                    for rec_id, rec_data in data.items():
                        if rec_data.get("created_at"):
                            rec_data["created_at"] = datetime.fromisoformat(rec_data["created_at"])
                        self.recommendations[rec_id] = FinancialRecommendation(**rec_data)

        except Exception as exc:
            logger.error("Error loading wealth data: %s", exc)

    def _save_data(self) -> None:
        """Guardar datos financieros."""
        try:
            with open(INCOME_FILE, "w") as f:
                data = {k: asdict(v) for k, v in self.income.items()}
                json.dump(data, f, indent=2, default=str)

            with open(EXPENSES_FILE, "w") as f:
                data = {k: asdict(v) for k, v in self.expenses.items()}
                json.dump(data, f, indent=2, default=str)

            with open(GOALS_FILE, "w") as f:
                data = {k: asdict(v) for k, v in self.goals.items()}
                json.dump(data, f, indent=2, default=str)

            with open(RECOMMENDATIONS_FILE, "w") as f:
                data = {k: asdict(v) for k, v in self.recommendations.items()}
                json.dump(data, f, indent=2, default=str)

        except Exception as exc:
            logger.error("Error saving wealth data: %s", exc)

    def add_income(self, source: IncomeSource, amount: Decimal, currency: str, platform: str, description: str, account_id: str) -> IncomeEntry:
        """Agregar ingreso."""
        entry_id = f"income_{datetime.now().timestamp()}"

        entry = IncomeEntry(
            entry_id=entry_id,
            source=source,
            amount=amount,
            currency=currency,
            date=datetime.now(),
            platform=platform,
            description=description,
            account_id=account_id,
        )

        self.income[entry_id] = entry
        self._save_data()
        self._generate_recommendations()
        return entry

    def add_expense(self, category: ExpenseCategory, amount: Decimal, currency: str, description: str, is_deductible: bool = False) -> ExpenseEntry:
        """Agregar gasto."""
        entry_id = f"expense_{datetime.now().timestamp()}"

        entry = ExpenseEntry(
            entry_id=entry_id,
            category=category,
            amount=amount,
            currency=currency,
            date=datetime.now(),
            description=description,
            is_deductible=is_deductible,
        )

        self.expenses[entry_id] = entry
        self._save_data()
        self._generate_recommendations()
        return entry

    def create_goal(self, title: str, target_amount: Decimal, currency: str, deadline: datetime, category: str) -> FinancialGoal:
        """Crear meta financiera."""
        goal_id = f"goal_{datetime.now().timestamp()}"

        goal = FinancialGoal(
            goal_id=goal_id,
            title=title,
            target_amount=target_amount,
            current_amount=Decimal("0"),
            currency=currency,
            deadline=deadline,
            category=category,
        )

        self.goals[goal_id] = goal
        self._save_data()
        return goal

    def update_goal_progress(self, goal_id: str, amount: Decimal) -> bool:
        """Actualizar progreso de meta."""
        if goal_id not in self.goals:
            return False

        self.goals[goal_id].current_amount = amount

        if amount >= self.goals[goal_id].target_amount:
            self.goals[goal_id].status = "completed"

        self._save_data()
        return True

    def get_monthly_summary(self, year: int, month: int) -> dict[str, Any]:
        """Obtener resumen mensual."""
        # Filtrar ingresos del mes
        month_income = [
            entry for entry in self.income.values()
            if entry.date.year == year and entry.date.month == month
        ]

        # Filtrar gastos del mes
        month_expenses = [
            entry for entry in self.expenses.values()
            if entry.date.year == year and entry.date.month == month
        ]

        total_income = sum(entry.amount for entry in month_income)
        total_expenses = sum(entry.amount for entry in month_expenses)
        net_income = total_income - total_expenses

        # Ingresos por fuente
        income_by_source = {}
        for entry in month_income:
            if entry.source.value not in income_by_source:
                income_by_source[entry.source.value] = Decimal("0")
            income_by_source[entry.source.value] += entry.amount

        # Gastos por categoría
        expenses_by_category = {}
        for entry in month_expenses:
            if entry.category.value not in expenses_by_category:
                expenses_by_category[entry.category.value] = Decimal("0")
            expenses_by_category[entry.category.value] += entry.amount

        return {
            "year": year,
            "month": month,
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "net_income": float(net_income),
            "income_by_source": {k: float(v) for k, v in income_by_source.items()},
            "expenses_by_category": {k: float(v) for k, v in expenses_by_category.items()},
            "income_count": len(month_income),
            "expense_count": len(month_expenses),
        }

    def get_annual_summary(self, year: int) -> dict[str, Any]:
        """Obtener resumen anual."""
        months = []
        for month in range(1, 13):
            month_summary = self.get_monthly_summary(year, month)
            months.append(month_summary)

        total_income = sum(m["total_income"] for m in months)
        total_expenses = sum(m["total_expenses"] for m in months)
        net_income = total_income - total_expenses

        return {
            "year": year,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_income": net_income,
            "monthly_breakdown": months,
        }

    def get_tax_prep_summary(self, year: int) -> dict[str, Any]:
        """Obtener resumen para preparación fiscal (Argentina/ARCA friendly)."""
        year_income = [
            entry for entry in self.income.values()
            if entry.date.year == year
        ]

        year_expenses = [
            entry for entry in self.expenses.values()
            if entry.date.year == year and entry.is_deductible
        ]

        total_income = sum(entry.amount for entry in year_income)
        total_deductible = sum(entry.amount for entry in year_expenses)

        # Por plataforma
        income_by_platform = {}
        for entry in year_income:
            if entry.platform not in income_by_platform:
                income_by_platform[entry.platform] = Decimal("0")
            income_by_platform[entry.platform] += entry.amount

        return {
            "year": year,
            "total_income": float(total_income),
            "total_deductible_expenses": float(total_deductible),
            "taxable_income": float(total_income - total_deductible),
            "income_by_platform": {k: float(v) for k, v in income_by_platform.items()},
            "income_entries": len(year_income),
            "deductible_expenses": len(year_expenses),
            "note": "Este resumen es informativo. Consulta con un contador para tu situación fiscal específica.",
        }

    def _generate_recommendations(self) -> None:
        """Generar recomendaciones automáticas basadas en datos."""
        current_date = datetime.now()
        rec_id = f"rec_{current_date.timestamp()}"

        # Recomendación: Configurar método de cobro si hay ingresos pendientes
        pending_income = [entry for entry in self.income.values() if entry.status == "pending"]
        if pending_income:
            self.recommendations[rec_id] = FinancialRecommendation(
                recommendation_id=rec_id,
                title="Configurar método de cobro",
                description=f"Tienes {len(pending_income)} ingresos pendientes. Configura tu cuenta Wise o PayPal para recibir pagos.",
                priority="high",
                estimated_impact="Perderás ingresos si no configuras método de cobro",
                action_required="Ir a Wealth > Integraciones y configurar cuenta",
                created_at=current_date,
            )

        # Recomendación: Separar porcentaje para impuestos
        current_year_income = [
            entry for entry in self.income.values()
            if entry.date.year == current_date.year
        ]
        if current_year_income:
            total = sum(entry.amount for entry in current_year_income)
            if total > Decimal("1000"):  # Si tiene más de $1000 en ingresos
                self.recommendations[rec_id + "_tax"] = FinancialRecommendation(
                    recommendation_id=rec_id + "_tax",
                    title="Separar porcentaje para impuestos",
                    description=f"Tienes ${float(total):.2f} en ingresos este año. Separa el 15-20% para impuestos.",
                    priority="medium",
                    estimated_impact="Evitar problemas fiscales al fin de año",
                    action_required="Crear cuenta separada para impuestos",
                    created_at=current_date,
                )

        self._save_data()

    def get_financial_health(self) -> dict[str, Any]:
        """Obtener salud financiera general."""
        current_date = datetime.now()
        current_month_income = [
            entry for entry in self.income.values()
            if entry.date.month == current_date.month and entry.date.year == current_date.year
        ]

        current_month_expenses = [
            entry for entry in self.expenses.values()
            if entry.date.month == current_date.month and entry.date.year == current_date.year
        ]

        monthly_income = sum(entry.amount for entry in current_month_income)
        monthly_expenses = sum(entry.amount for entry in current_month_expenses)
        savings_rate = (monthly_income - monthly_expenses) / monthly_income if monthly_income > 0 else Decimal("0")

        # Metas próximas a vencer
        upcoming_goals = [
            goal for goal in self.goals.values()
            if goal.deadline > current_date and goal.deadline < current_date + timedelta(days=30)
        ]

        return {
            "monthly_income": float(monthly_income),
            "monthly_expenses": float(monthly_expenses),
            "savings_rate": float(savings_rate),
            "pending_income": len([e for e in self.income.values() if e.status == "pending"]),
            "active_goals": len(self.goals),
            "upcoming_goals": len(upcoming_goals),
            "health_score": self._calculate_health_score(monthly_income, monthly_expenses, savings_rate),
        }

    def _calculate_health_score(self, income: Decimal, expenses: Decimal, savings_rate: Decimal) -> int:
        """Calcular score de salud financiera (0-100)."""
        score = 50  # Base

        if income > 0:
            if savings_rate >= Decimal("0.2"):
                score += 30
            elif savings_rate >= Decimal("0.1"):
                score += 20
            elif savings_rate >= Decimal("0.05"):
                score += 10

        if expenses < income:
            score += 10

        if len(self.goals) > 0:
            score += 10

        return min(score, 100)


# Singleton instance
_wealth_assistant: WealthAssistant | None = None


def get_wealth_assistant() -> WealthAssistant:
    """Obtener instancia singleton del Wealth Assistant."""
    global _wealth_assistant
    if _wealth_assistant is None:
        _wealth_assistant = WealthAssistant()
    return _wealth_assistant


def reset_wealth_assistant() -> None:
    """Resetear instancia singleton."""
    global _wealth_assistant
    _wealth_assistant = None