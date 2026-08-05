"""Financial Models — Core data structures for personal finance command center."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4


class TransactionType(str, Enum):
    """Type of financial transaction."""

    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    INVESTMENT = "investment"
    REWARD = "reward"


class IncomeCategory(str, Enum):
    """Categories for income sources."""

    FREELANCE = "freelance"
    BOUNTY = "bounty"
    DEV_BOUNTY = "dev_bounty"
    DATA_ENTRY = "data_entry"
    MICROTASK = "microtask"
    COMPETITION = "competition"
    INVESTMENT = "investment"
    PASSIVE = "passive"
    OTHER = "other"


class ExpenseCategory(str, Enum):
    """Categories for expenses."""

    HOUSING = "housing"
    FOOD = "food"
    TRANSPORT = "transport"
    UTILITIES = "utilities"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    TECHNOLOGY = "technology"
    PRODUCTIVITY = "productivity"
    BUSINESS = "business"
    ENTERTAINMENT = "entertainment"
    SUBSCRIPTIONS = "subscriptions"
    TAXES = "taxes"
    INSURANCE = "insurance"
    SAVINGS = "savings"
    INVESTMENTS = "investments"
    OTHER = "other"


class OpportunityStatus(str, Enum):
    """Status of a tracked opportunity."""

    DISCOVERED = "discovered"
    EVALUATING = "evaluating"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    PAID = "paid"
    REJECTED = "rejected"
    ABANDONED = "abandoned"


class AssetType(str, Enum):
    """Type of financial asset."""

    CASH = "cash"
    BANK = "bank"
    CRYPTO = "crypto"
    INVESTMENT = "investment"
    RECEIVABLE = "receivable"
    DIGITAL_ASSET = "digital_asset"
    SKILL = "skill"
    PORTFOLIO_ITEM = "portfolio_item"


@dataclass(slots=True)
class Transaction:
    """A single financial transaction."""

    id: str = field(default_factory=lambda: str(uuid4()))
    date: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    type: TransactionType = TransactionType.EXPENSE
    category: str = ""
    subcategory: str = ""
    description: str = ""
    source: str = ""  # platform, client, account
    tags: list[str] = field(default_factory=list)
    related_opportunity_id: str | None = None
    related_workbank_id: str | None = None
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date,
            "amount": str(self.amount),
            "currency": self.currency,
            "type": self.type.value,
            "category": self.category,
            "subcategory": self.subcategory,
            "description": self.description,
            "source": self.source,
            "tags": self.tags,
            "related_opportunity_id": self.related_opportunity_id,
            "related_workbank_id": self.related_workbank_id,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(slots=True)
class Opportunity:
    """A tracked income opportunity from discovery to payment."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    platform: str = ""
    category: IncomeCategory = IncomeCategory.OTHER
    status: OpportunityStatus = OpportunityStatus.DISCOVERED
    expected_reward: Decimal = Decimal("0")
    currency: str = "USD"
    success_probability: float = 0.5  # 0.0 - 1.0
    human_time_hours: float = 0.0
    actual_time_hours: float = 0.0
    actual_reward: Decimal = Decimal("0")
    discovered_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str | None = None
    submitted_at: str | None = None
    completed_at: str | None = None
    paid_at: str | None = None
    platform_url: str = ""
    workbank_id: str | None = None
    skills_required: list[str] = field(default_factory=list)
    skills_gained: list[str] = field(default_factory=list)
    reusable_assets: list[str] = field(default_factory=list)
    notes: str = ""
    ev_score: float = 0.0  # Expected Value per hour
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def ev_per_hour(self) -> float:
        """Calculate EV per hour."""
        if self.human_time_hours <= 0:
            return 0.0
        return float(self.expected_reward * Decimal(str(self.success_probability))) / self.human_time_hours

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "platform": self.platform,
            "category": self.category.value if hasattr(self.category, "value") else self.category,
            "status": self.status.value if hasattr(self.status, "value") else self.status,
            "expected_reward": str(self.expected_reward),
            "currency": self.currency,
            "success_probability": self.success_probability,
            "human_time_hours": self.human_time_hours,
            "actual_time_hours": self.actual_time_hours,
            "actual_reward": str(self.actual_reward),
            "discovered_at": self.discovered_at,
            "started_at": self.started_at,
            "submitted_at": self.submitted_at,
            "completed_at": self.completed_at,
            "paid_at": self.paid_at,
            "platform_url": self.platform_url,
            "workbank_id": self.workbank_id,
            "skills_required": self.skills_required,
            "skills_gained": self.skills_gained,
            "reusable_assets": self.reusable_assets,
            "notes": self.notes,
            "ev_score": self.ev_score,
            "ev_per_hour": self.ev_per_hour,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(slots=True)
class FinancialAsset:
    """A financial asset or resource."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    type: AssetType = AssetType.CASH
    value: Decimal = Decimal("0")
    currency: str = "USD"
    platform: str = ""
    account_id: str = ""
    description: str = ""
    liquid: bool = True
    last_updated: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "value": str(self.value),
            "currency": self.currency,
            "platform": self.platform,
            "account_id": self.account_id,
            "description": self.description,
            "liquid": self.liquid,
            "last_updated": self.last_updated,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class WorkIncomeRecord:
    """Record of completed work linked to financial outcome."""

    id: str = field(default_factory=lambda: str(uuid4()))
    workbank_id: str = ""
    opportunity_id: str | None = None
    platform: str = ""
    title: str = ""
    category: IncomeCategory = IncomeCategory.OTHER
    time_invested_hours: float = 0.0
    reward: Decimal = Decimal("0")
    currency: str = "USD"
    profit_per_hour: float = 0.0
    skills_improved: list[str] = field(default_factory=list)
    reusable_assets_created: list[str] = field(default_factory=list)
    completed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    paid_at: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workbank_id": self.workbank_id,
            "opportunity_id": self.opportunity_id,
            "platform": self.platform,
            "title": self.title,
            "category": self.category.value,
            "time_invested_hours": self.time_invested_hours,
            "reward": str(self.reward),
            "currency": self.currency,
            "profit_per_hour": self.profit_per_hour,
            "skills_improved": self.skills_improved,
            "reusable_assets_created": self.reusable_assets_created,
            "completed_at": self.completed_at,
            "paid_at": self.paid_at,
            "notes": self.notes,
        }


@dataclass(slots=True)
class BudgetCategory:
    """Budget allocation for a category."""

    category: str
    allocated: Decimal = Decimal("0")
    spent: Decimal = Decimal("0")
    currency: str = "USD"
    period: str = "monthly"  # weekly, monthly, yearly

    @property
    def remaining(self) -> Decimal:
        return self.allocated - self.spent

    @property
    def utilization_pct(self) -> float:
        if self.allocated == 0:
            return 0.0
        return float(self.spent / self.allocated * 100)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "allocated": str(self.allocated),
            "spent": str(self.spent),
            "remaining": str(self.remaining),
            "currency": self.currency,
            "period": self.period,
            "utilization_pct": round(self.utilization_pct, 1),
        }


@dataclass(slots=True)
class FinancialSummary:
    """Periodic financial summary."""

    period_start: str
    period_end: str
    total_income: Decimal = Decimal("0")
    total_expenses: Decimal = Decimal("0")
    net_income: Decimal = Decimal("0")
    total_opportunities: int = 0
    completed_opportunities: int = 0
    pending_opportunities: int = 0
    total_work_hours: float = 0.0
    avg_profit_per_hour: float = 0.0
    top_platforms: list[dict] = field(default_factory=list)
    top_categories: list[dict] = field(default_factory=list)
    savings_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "period_start": self.period_start,
            "period_end": self.period_end,
            "total_income": str(self.total_income),
            "total_expenses": str(self.total_expenses),
            "net_income": str(self.net_income),
            "total_opportunities": self.total_opportunities,
            "completed_opportunities": self.completed_opportunities,
            "pending_opportunities": self.pending_opportunities,
            "total_work_hours": self.total_work_hours,
            "avg_profit_per_hour": round(self.avg_profit_per_hour, 2),
            "top_platforms": self.top_platforms,
            "top_categories": self.top_categories,
            "savings_rate": round(self.savings_rate, 1),
        }


@dataclass(slots=True)
class FreedomProgress:
    """Financial freedom tracking."""

    monthly_target: Decimal = Decimal("5000")
    current_monthly_avg: Decimal = Decimal("0")
    recurring_income: Decimal = Decimal("0")
    active_income_systems: int = 0
    emergency_fund_months: float = 0.0
    progress_pct: float = 0.0
    months_to_target: float = 0.0
    last_calculated: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "monthly_target": str(self.monthly_target),
            "current_monthly_avg": str(self.current_monthly_avg),
            "recurring_income": str(self.recurring_income),
            "active_income_systems": self.active_income_systems,
            "emergency_fund_months": round(self.emergency_fund_months, 1),
            "progress_pct": round(self.progress_pct, 1),
            "months_to_target": round(self.months_to_target, 1),
            "last_calculated": self.last_calculated,
        }
