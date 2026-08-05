"""Finance API Router — Personal Finance Command Center endpoints."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from cores.finance.engine import FinanceEngine, get_finance_engine
from cores.finance.models import (
    ExpenseCategory,
    FinancialAsset,
    IncomeCategory,
    Opportunity,
    OpportunityStatus,
    Transaction,
    TransactionType,
    WorkIncomeRecord,
)
from cores.finance.store import FinanceStore, get_finance_store

logger = logging.getLogger("ownex.api.finance")

router = APIRouter(prefix="/finance", tags=["finance"])

# ─── Request/Response Models ───


class TransactionCreate(BaseModel):
    amount: str
    currency: str = "USD"
    type: TransactionType
    category: str
    subcategory: str = ""
    description: str = ""
    source: str = ""
    tags: list[str] = []
    related_opportunity_id: str | None = None
    related_workbank_id: str | None = None
    notes: str = ""


class TransactionUpdate(BaseModel):
    amount: str | None = None
    category: str | None = None
    subcategory: str | None = None
    description: str | None = None
    source: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


class OpportunityCreate(BaseModel):
    title: str
    platform: str
    category: IncomeCategory = IncomeCategory.OTHER
    expected_reward: str
    currency: str = "USD"
    success_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    human_time_hours: float = Field(default=0.0, ge=0.0)
    platform_url: str = ""
    workbank_id: str | None = None
    skills_required: list[str] = []
    notes: str = ""


class OpportunityUpdate(BaseModel):
    status: OpportunityStatus | None = None
    actual_time_hours: float | None = None
    actual_reward: str | None = None
    skills_gained: list[str] | None = None
    reusable_assets: list[str] | None = None
    notes: str | None = None


class WorkIncomeCreate(BaseModel):
    workbank_id: str
    opportunity_id: str | None = None
    platform: str
    title: str
    category: IncomeCategory = IncomeCategory.OTHER
    time_invested_hours: float = Field(default=0.0, ge=0.0)
    reward: str
    currency: str = "USD"
    skills_improved: list[str] = []
    reusable_assets_created: list[str] = []
    notes: str = ""


class BudgetCreate(BaseModel):
    category: ExpenseCategory
    allocated: str
    period: str = "monthly"


class AssetCreate(BaseModel):
    name: str
    type: str
    value: str
    currency: str = "USD"
    platform: str = ""
    account_id: str = ""
    description: str = ""
    liquid: bool = True
    metadata: dict = {}


class FreedomProgressUpdate(BaseModel):
    monthly_target: str | None = None
    recurring_income: str | None = None
    active_income_systems: int | None = None


# ─── Helpers ───


def _get_engine() -> FinanceEngine:
    return get_finance_engine()


def _get_store() -> FinanceStore:
    return get_finance_store()


def _decimal_or_none(v: str | None) -> Decimal | None:
    return Decimal(v) if v is not None else None


# ─── Transactions ───


@router.post("/transactions", response_model=dict)
async def create_transaction(txn: TransactionCreate) -> dict[str, Any]:
    """Create a new transaction."""
    from cores.finance.store import get_finance_store

    store = get_finance_store()
    transaction = Transaction(
        amount=Decimal(txn.amount),
        currency=txn.currency,
        type=txn.type,
        category=txn.category,
        subcategory=txn.subcategory,
        description=txn.description,
        source=txn.source,
        tags=txn.tags,
        related_opportunity_id=txn.related_opportunity_id,
        related_workbank_id=txn.related_workbank_id,
        notes=txn.notes,
    )
    stored = store.add_transaction(transaction)
    return stored.to_dict()


@router.get("/transactions", response_model=dict)
async def list_transactions(
    type: TransactionType | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(default=100, le=1000),
) -> dict[str, Any]:
    """List transactions with optional filters."""
    store = _get_store()
    transactions = store.get_transactions(
        type_=type,
        category=category,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return {
        "total": len(transactions),
        "transactions": [t.to_dict() for t in transactions],
    }


@router.get("/transactions/{txn_id}", response_model=dict)
async def get_transaction(txn_id: str) -> dict[str, Any]:
    """Get a single transaction."""
    store = _get_store()
    txn = store.get_transaction(txn_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn.to_dict()


@router.patch("/transactions/{txn_id}", response_model=dict)
async def update_transaction(txn_id: str, update: TransactionUpdate) -> dict[str, Any]:
    """Update a transaction."""
    store = _get_store()
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if "amount" in update_data:
        update_data["amount"] = Decimal(update_data["amount"])
    txn = store.update_transaction(txn_id, **update_data)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn.to_dict()


@router.delete("/transactions/{txn_id}", response_model=dict)
async def delete_transaction(txn_id: str) -> dict[str, Any]:
    """Delete a transaction."""
    store = _get_store()
    success = store.delete_transaction(txn_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"success": True, "id": txn_id}


# ─── Opportunities ───


@router.post("/opportunities", response_model=dict)
async def create_opportunity(opp: OpportunityCreate) -> dict[str, Any]:
    """Create a new tracked opportunity."""
    store = _get_store()
    opportunity = Opportunity(
        title=opp.title,
        platform=opp.platform,
        category=opp.category,
        expected_reward=Decimal(opp.expected_reward),
        currency=opp.currency,
        success_probability=opp.success_probability,
        human_time_hours=opp.human_time_hours,
        platform_url=opp.platform_url,
        workbank_id=opp.workbank_id,
        skills_required=opp.skills_required,
        notes=opp.notes,
    )
    stored = store.add_opportunity(opportunity)
    return stored.to_dict()


@router.get("/opportunities", response_model=dict)
async def list_opportunities(
    status: OpportunityStatus | None = None,
    platform: str | None = None,
    category: IncomeCategory | None = None,
) -> dict[str, Any]:
    """List opportunities with optional filters."""
    store = _get_store()
    opportunities = store.get_opportunities(status=status, platform=platform, category=category)
    return {
        "total": len(opportunities),
        "opportunities": [o.to_dict() for o in opportunities],
    }


@router.get("/opportunities/pipeline", response_model=dict)
async def get_pipeline_summary() -> dict[str, Any]:
    """Get opportunity pipeline counts by status."""
    engine = _get_engine()
    return {"pipeline": engine.get_pipeline_summary()}


@router.get("/opportunities/top", response_model=dict)
async def get_top_opportunities(limit: int = Query(default=10, le=50)) -> dict[str, Any]:
    """Get top opportunities ranked by EV."""
    engine = _get_engine()
    top = engine.get_top_opportunities(limit)
    return {"opportunities": [o.to_dict() for o in top]}


@router.get("/opportunities/{opp_id}", response_model=dict)
async def get_opportunity(opp_id: str) -> dict[str, Any]:
    """Get a single opportunity."""
    store = _get_store()
    opp = store.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp.to_dict()


@router.patch("/opportunities/{opp_id}", response_model=dict)
async def update_opportunity(opp_id: str, update: OpportunityUpdate) -> dict[str, Any]:
    """Update an opportunity."""
    store = _get_store()
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if "actual_reward" in update_data:
        update_data["actual_reward"] = Decimal(update_data["actual_reward"])
    opp = store.update_opportunity(opp_id, **update_data)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp.to_dict()


# ─── Work Income ───


@router.post("/work-income", response_model=dict)
async def record_work_income(record: WorkIncomeCreate) -> dict[str, Any]:
    """Record completed work with financial outcome."""
    store = _get_store()
    wi = WorkIncomeRecord(
        workbank_id=record.workbank_id,
        opportunity_id=record.opportunity_id,
        platform=record.platform,
        title=record.title,
        category=record.category,
        time_invested_hours=record.time_invested_hours,
        reward=Decimal(record.reward),
        currency=record.currency,
        profit_per_hour=float(Decimal(record.reward)) / record.time_invested_hours
        if record.time_invested_hours > 0
        else 0.0,
        skills_improved=record.skills_improved,
        reusable_assets_created=record.reusable_assets_created,
        notes=record.notes,
    )
    stored = store.add_work_income(wi)
    return stored.to_dict()


@router.get("/work-income", response_model=dict)
async def list_work_income(
    platform: str | None = None,
    limit: int = Query(default=50, le=200),
) -> dict[str, Any]:
    """List completed work income records."""
    store = _get_store()
    if platform:
        records = store.get_work_income_by_platform(platform)
    else:
        records = store.get_work_income(limit=limit)
    return {
        "total": len(records),
        "records": [r.to_dict() for r in records],
    }


@router.get("/work-income/analysis", response_model=dict)
async def analyze_work_income(days: int = Query(default=30, le=365)) -> dict[str, Any]:
    """Analyze work income patterns."""
    engine = _get_engine()
    return engine.analyze_work_income(days)


@router.get("/work-income/platform/{platform}", response_model=dict)
async def get_platform_analysis(platform: str) -> dict[str, Any]:
    """Get detailed analysis for a specific platform."""
    engine = _get_engine()
    return engine.get_work_income_by_platform(platform)


# ─── Budgets ───


@router.post("/budgets", response_model=dict)
async def create_budget(budget: BudgetCreate) -> dict[str, Any]:
    """Set budget for a category."""
    store = _get_store()
    b = store.set_budget(budget.category, Decimal(budget.allocated), budget.period)
    return b.to_dict()


@router.get("/budgets", response_model=dict)
async def list_budgets() -> dict[str, Any]:
    """Get all budget categories."""
    store = _get_store()
    budgets = store.get_all_budgets()
    return {"budgets": [b.to_dict() for b in budgets]}


@router.get("/budgets/alerts", response_model=dict)
async def check_budget_alerts(threshold: float = Query(default=80.0, le=100.0)) -> dict[str, Any]:
    """Check for budgets exceeding threshold."""
    engine = _get_engine()
    alerts = engine.check_budget_alerts(threshold)
    return {"alerts": alerts, "threshold": threshold}


@router.post("/budgets/expense", response_model=dict)
async def record_budget_expense(category: ExpenseCategory, amount: str) -> dict[str, Any]:
    """Record an expense against a budget category."""
    store = _get_store()
    budget = store.record_expense(category, Decimal(amount))
    if not budget:
        raise HTTPException(status_code=404, detail="Budget category not found")
    return budget.to_dict()


# ─── Assets ───


@router.post("/assets", response_model=dict)
async def create_asset(asset: AssetCreate) -> dict[str, Any]:
    """Create a financial asset."""
    store = _get_store()
    a = FinancialAsset(
        name=asset.name,
        type=asset.type,
        value=Decimal(asset.value),
        currency=asset.currency,
        platform=asset.platform,
        account_id=asset.account_id,
        description=asset.description,
        liquid=asset.liquid,
        metadata=asset.metadata,
    )
    stored = store.add_asset(a)
    return stored.to_dict()


@router.get("/assets", response_model=dict)
async def list_assets() -> dict[str, Any]:
    """List all financial assets."""
    store = _get_store()
    assets = store.get_assets()
    total = store.get_total_assets_value()
    return {
        "total_value": str(total),
        "assets": [a.to_dict() for a in assets],
    }


# ─── Summaries ───


@router.post("/summaries/generate", response_model=dict)
async def generate_summary() -> dict[str, Any]:
    """Generate monthly financial summary."""
    engine = _get_engine()
    summary = engine.generate_monthly_summary()
    return summary.to_dict()


@router.get("/summaries", response_model=dict)
async def list_summaries(limit: int = Query(default=12, le=60)) -> dict[str, Any]:
    """List financial summaries."""
    store = _get_store()
    summaries = store.get_summaries(limit=limit)
    return {"summaries": [s.to_dict() for s in summaries]}


@router.get("/summaries/latest", response_model=dict)
async def get_latest_summary() -> dict[str, Any]:
    """Get the latest monthly summary."""
    engine = _get_engine()
    summary = engine.get_latest_summary()
    if not summary:
        return {"summary": None}
    return {"summary": summary.to_dict()}


# ─── Freedom Progress ───


@router.get("/freedom", response_model=dict)
async def get_freedom_progress() -> dict[str, Any]:
    """Get financial freedom progress."""
    engine = _get_engine()
    fp = engine.calculate_freedom_progress()
    return fp.to_dict()


@router.patch("/freedom", response_model=dict)
async def update_freedom_progress(update: FreedomProgressUpdate) -> dict[str, Any]:
    """Update freedom progress targets."""
    store = _get_store()
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if "monthly_target" in update_data:
        update_data["monthly_target"] = Decimal(update_data["monthly_target"])
    if "recurring_income" in update_data:
        update_data["recurring_income"] = Decimal(update_data["recurring_income"])
    fp = store.update_freedom_progress(**update_data)
    return fp.to_dict()


# ─── Daily Briefing ───


@router.get("/briefing/daily", response_model=dict)
async def get_daily_briefing() -> dict[str, Any]:
    """Get the daily financial briefing."""
    engine = _get_engine()
    return engine.generate_daily_briefing()


# ─── Analytics ───


@router.get("/analytics/spending", response_model=dict)
async def get_spending_analysis(days: int = Query(default=30, le=365)) -> dict[str, Any]:
    """Analyze spending patterns."""
    engine = _get_engine()
    return engine.analyze_spending(days)


@router.get("/analytics/income", response_model=dict)
async def get_income_analysis(days: int = Query(default=30, le=365)) -> dict[str, Any]:
    """Analyze income patterns."""
    engine = _get_engine()
    return engine.analyze_income(days)


@router.get("/analytics/work-income", response_model=dict)
async def get_work_income_analysis(days: int = Query(default=30, le=365)) -> dict[str, Any]:
    """Analyze work income patterns."""
    engine = _get_engine()
    return engine.analyze_work_income(days)


@router.get("/analytics/opportunities", response_model=dict)
async def get_opportunities_analysis() -> dict[str, Any]:
    """Analyze opportunity pipeline."""
    engine = _get_engine()
    pipeline = engine.get_pipeline_summary()
    top = engine.get_top_opportunities(10)
    return {
        "pipeline": pipeline,
        "top_opportunities": [o.to_dict() for o in top],
    }


# ─── Quick Actions ───


@router.post("/quick/record-income", response_model=dict)
async def quick_record_income(
    amount: str,
    category: IncomeCategory,
    source: str,
    description: str = "",
) -> dict[str, Any]:
    """Quickly record an income transaction."""
    store = _get_store()
    txn = Transaction(
        amount=Decimal(amount),
        type=TransactionType.INCOME,
        category=category.value,
        description=description,
        source=source,
    )
    stored = store.add_transaction(txn)
    return stored.to_dict()


@router.post("/quick/record-expense", response_model=dict)
async def quick_record_expense(
    amount: str,
    category: ExpenseCategory,
    source: str,
    description: str = "",
) -> dict[str, Any]:
    """Quickly record an expense transaction."""
    store = _get_store()
    txn = Transaction(
        amount=Decimal(amount),
        type=TransactionType.EXPENSE,
        category=category.value,
        description=description,
        source=source,
    )
    stored = store.add_transaction(txn)
    return stored.to_dict()


@router.post("/quick/complete-work", response_model=dict)
async def quick_complete_work(
    workbank_id: str,
    platform: str,
    title: str,
    reward: str,
    time_hours: float,
    category: IncomeCategory = IncomeCategory.OTHER,
) -> dict[str, Any]:
    """Quickly record completed work from workbank."""
    store = _get_store()
    wi = WorkIncomeRecord(
        workbank_id=workbank_id,
        platform=platform,
        title=title,
        category=category,
        time_invested_hours=time_hours,
        reward=Decimal(reward),
        profit_per_hour=float(Decimal(reward)) / time_hours if time_hours > 0 else 0.0,
    )
    stored = store.add_work_income(wi)
    return stored.to_dict()


def register_finance_capabilities() -> None:
    """Register Finance Engine capabilities in the CapabilityRegistry."""
    try:
        from core.capabilities.registry import get_capability_registry

        reg = get_capability_registry()
        reg.unregister("finance", "finance_engine")
        reg.register(
            "finance",
            "finance_engine",
            {
                "capabilities": [
                    "transaction_tracking",
                    "opportunity_management",
                    "work_income_tracking",
                    "budget_management",
                    "financial_analysis",
                    "freedom_progress",
                    "daily_briefing",
                ]
            },
            description="Personal finance command center with EV-based opportunity ranking",
        )
        logger.info("Finance Engine registered in CapabilityRegistry")
    except Exception as exc:
        logger.warning("Could not register Finance Engine in CapabilityRegistry: %s", exc)
