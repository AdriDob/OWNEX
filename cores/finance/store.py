"""Finance Store — Persistent storage for financial data using JSON files."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from cores.finance.models import (
    BudgetCategory,
    ExpenseCategory,
    FinancialAsset,
    FinancialSummary,
    FreedomProgress,
    IncomeCategory,
    Opportunity,
    OpportunityStatus,
    Transaction,
    TransactionType,
    WorkIncomeRecord,
)

logger = logging.getLogger("ownex.finance.store")


class FinanceStore:
    """Persistent storage for all financial data."""

    def __init__(self, store_dir: str | Path | None = None):
        self._store_dir = Path(store_dir or Path(__file__).resolve().parents[3] / "data" / "finance")
        self._store_dir.mkdir(parents=True, exist_ok=True)

        self._transactions_file = self._store_dir / "transactions.json"
        self._opportunities_file = self._store_dir / "opportunities.json"
        self._assets_file = self._store_dir / "assets.json"
        self._work_income_file = self._store_dir / "work_income.json"
        self._budgets_file = self._store_dir / "budgets.json"
        self._summaries_file = self._store_dir / "summaries.json"
        self._freedom_file = self._store_dir / "freedom_progress.json"

        # In-memory caches
        self._transactions: dict[str, Transaction] = {}
        self._opportunities: dict[str, Opportunity] = {}
        self._assets: dict[str, FinancialAsset] = {}
        self._work_income: dict[str, WorkIncomeRecord] = {}
        self._budgets: dict[str, BudgetCategory] = {}
        self._summaries: list[FinancialSummary] = []
        self._freedom_progress: FreedomProgress | None = None

        self._load_all()

    def _load_all(self) -> None:
        """Load all data from disk."""
        self._load_transactions()
        self._load_opportunities()
        self._load_assets()
        self._load_work_income()
        self._load_budgets()
        self._load_summaries()
        self._load_freedom_progress()

    # ── Transactions ──
    def _load_transactions(self) -> None:
        try:
            if self._transactions_file.exists():
                data = json.loads(self._transactions_file.read_text())
                for raw in data:
                    t = Transaction(
                        id=raw["id"],
                        date=raw["date"],
                        amount=Decimal(raw["amount"]),
                        currency=raw["currency"],
                        type=TransactionType(raw["type"]),
                        category=raw["category"],
                        subcategory=raw.get("subcategory", ""),
                        description=raw["description"],
                        source=raw["source"],
                        tags=raw.get("tags", []),
                        related_opportunity_id=raw.get("related_opportunity_id"),
                        related_workbank_id=raw.get("related_workbank_id"),
                        notes=raw.get("notes", ""),
                        created_at=raw["created_at"],
                        updated_at=raw["updated_at"],
                    )
                    self._transactions[t.id] = t
        except Exception as e:
            logger.warning(f"Could not load transactions: {e}")

    def _save_transactions(self) -> None:
        try:
            data = [t.to_dict() for t in self._transactions.values()]
            self._transactions_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Could not save transactions: {e}")

    def add_transaction(self, transaction: Transaction) -> Transaction:
        self._transactions[transaction.id] = transaction
        self._save_transactions()
        return transaction

    def get_transaction(self, txn_id: str) -> Transaction | None:
        return self._transactions.get(txn_id)

    def get_transactions(
        self,
        type_: TransactionType | None = None,
        category: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int | None = None,
    ) -> list[Transaction]:
        results = list(self._transactions.values())

        if type_:
            results = [t for t in results if t.type == type_]
        if category:
            results = [t for t in results if t.category == category]
        if start_date:
            results = [t for t in results if t.date >= start_date]
        if end_date:
            results = [t for t in results if t.date <= end_date]

        results.sort(key=lambda t: t.date, reverse=True)
        if limit:
            results = results[:limit]
        return results

    def get_income_transactions(self, **kwargs) -> list[Transaction]:
        return self.get_transactions(type_=TransactionType.INCOME, **kwargs)

    def get_expense_transactions(self, **kwargs) -> list[Transaction]:
        return self.get_transactions(type_=TransactionType.EXPENSE, **kwargs)

    def update_transaction(self, txn_id: str, **kwargs) -> Transaction | None:
        txn = self._transactions.get(txn_id)
        if not txn:
            return None
        for k, v in kwargs.items():
            if hasattr(txn, k):
                setattr(txn, k, v)
        txn.updated_at = datetime.now(UTC).isoformat()
        self._save_transactions()
        return txn

    def delete_transaction(self, txn_id: str) -> bool:
        if txn_id in self._transactions:
            del self._transactions[txn_id]
            self._save_transactions()
            return True
        return False

    # ── Opportunities ──
    def _load_opportunities(self) -> None:
        try:
            if self._opportunities_file.exists():
                data = json.loads(self._opportunities_file.read_text())
                for raw in data:
                    opp = Opportunity(
                        id=raw["id"],
                        title=raw["title"],
                        platform=raw["platform"],
                        category=IncomeCategory(raw["category"]),
                        status=OpportunityStatus(raw["status"]),
                        expected_reward=Decimal(raw["expected_reward"]),
                        currency=raw["currency"],
                        success_probability=raw["success_probability"],
                        human_time_hours=raw["human_time_hours"],
                        actual_time_hours=raw.get("actual_time_hours", 0.0),
                        actual_reward=Decimal(raw.get("actual_reward", "0")),
                        discovered_at=raw["discovered_at"],
                        started_at=raw.get("started_at"),
                        submitted_at=raw.get("submitted_at"),
                        completed_at=raw.get("completed_at"),
                        paid_at=raw.get("paid_at"),
                        platform_url=raw.get("platform_url", ""),
                        workbank_id=raw.get("workbank_id"),
                        skills_required=raw.get("skills_required", []),
                        skills_gained=raw.get("skills_gained", []),
                        reusable_assets=raw.get("reusable_assets", []),
                        notes=raw.get("notes", ""),
                        ev_score=raw.get("ev_score", 0.0),
                        created_at=raw["created_at"],
                        updated_at=raw["updated_at"],
                    )
                    self._opportunities[opp.id] = opp
        except Exception as e:
            logger.warning(f"Could not load opportunities: {e}")

    def _save_opportunities(self) -> None:
        try:
            data = [o.to_dict() for o in self._opportunities.values()]
            self._opportunities_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Could not save opportunities: {e}")

    def add_opportunity(self, opportunity: Opportunity) -> Opportunity:
        self._opportunities[opportunity.id] = opportunity
        self._save_opportunities()
        return opportunity

    def get_opportunity(self, opp_id: str) -> Opportunity | None:
        return self._opportunities.get(opp_id)

    def get_opportunities(
        self,
        status: OpportunityStatus | None = None,
        platform: str | None = None,
        category: IncomeCategory | None = None,
    ) -> list[Opportunity]:
        results = list(self._opportunities.values())

        if status:
            results = [o for o in results if o.status == status]
        if platform:
            results = [o for o in results if o.platform == platform]
        if category:
            results = [o for o in results if o.category == category]

        results.sort(key=lambda o: o.ev_score, reverse=True)
        return results

    def update_opportunity(self, opp_id: str, **kwargs) -> Opportunity | None:
        opp = self._opportunities.get(opp_id)
        if not opp:
            return None
        for k, v in kwargs.items():
            if hasattr(opp, k):
                setattr(opp, k, v)
        opp.updated_at = datetime.now(UTC).isoformat()
        self._save_opportunities()
        return opp

    # ── Assets ──
    def _load_assets(self) -> None:
        try:
            if self._assets_file.exists():
                data = json.loads(self._assets_file.read_text())
                for raw in data:
                    asset = FinancialAsset(
                        id=raw["id"],
                        name=raw["name"],
                        type=raw["type"],
                        value=Decimal(raw["value"]),
                        currency=raw["currency"],
                        platform=raw["platform"],
                        account_id=raw.get("account_id", ""),
                        description=raw.get("description", ""),
                        liquid=raw.get("liquid", True),
                        last_updated=raw.get("last_updated", datetime.now(UTC).isoformat()),
                        metadata=raw.get("metadata", {}),
                    )
                    self._assets[asset.id] = asset
        except Exception as e:
            logger.warning(f"Could not load assets: {e}")

    def _save_assets(self) -> None:
        try:
            data = [a.to_dict() for a in self._assets.values()]
            self._assets_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Could not save assets: {e}")

    def add_asset(self, asset: FinancialAsset) -> FinancialAsset:
        self._assets[asset.id] = asset
        self._save_assets()
        return asset

    def get_assets(self) -> list[FinancialAsset]:
        return list(self._assets.values())

    def get_total_assets_value(self, currency: str = "USD") -> Decimal:
        return sum(a.value for a in self._assets.values() if a.currency == currency)

    # ── Work Income Records ──
    def _load_work_income(self) -> None:
        try:
            if self._work_income_file.exists():
                data = json.loads(self._work_income_file.read_text())
                for raw in data:
                    rec = WorkIncomeRecord(
                        id=raw["id"],
                        workbank_id=raw["workbank_id"],
                        opportunity_id=raw.get("opportunity_id"),
                        platform=raw["platform"],
                        title=raw["title"],
                        category=IncomeCategory(raw["category"]),
                        time_invested_hours=raw["time_invested_hours"],
                        reward=Decimal(raw["reward"]),
                        currency=raw["currency"],
                        profit_per_hour=raw["profit_per_hour"],
                        skills_improved=raw.get("skills_improved", []),
                        reusable_assets_created=raw.get("reusable_assets_created", []),
                        completed_at=raw["completed_at"],
                        paid_at=raw.get("paid_at"),
                        notes=raw.get("notes", ""),
                    )
                    self._work_income[rec.id] = rec
        except Exception as e:
            logger.warning(f"Could not load work income: {e}")

    def _save_work_income(self) -> None:
        try:
            data = [r.to_dict() for r in self._work_income.values()]
            self._work_income_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Could not save work income: {e}")

    def add_work_income(self, record: WorkIncomeRecord) -> WorkIncomeRecord:
        self._work_income[record.id] = record
        self._save_work_income()
        return record

    def get_work_income(self, limit: int | None = None) -> list[WorkIncomeRecord]:
        records = sorted(self._work_income.values(), key=lambda r: r.completed_at, reverse=True)
        if limit:
            return records[:limit]
        return records

    def get_work_income_by_platform(self, platform: str) -> list[WorkIncomeRecord]:
        return [r for r in self._work_income.values() if r.platform == platform]

    # ── Budgets ──
    def _load_budgets(self) -> None:
        try:
            if self._budgets_file.exists():
                data = json.loads(self._budgets_file.read_text())
                for raw in data:
                    cat = raw["category"]
                    try:
                        cat_enum = ExpenseCategory(cat)
                        key = cat_enum.value
                    except ValueError:
                        key = cat
                    self._budgets[key] = BudgetCategory(
                        category=cat,
                        allocated=Decimal(raw["allocated"]),
                        spent=Decimal(raw.get("spent", "0")),
                        currency=raw.get("currency", "USD"),
                        period=raw.get("period", "monthly"),
                    )
        except Exception as e:
            logger.warning(f"Could not load budgets: {e}")

    def _save_budgets(self) -> None:
        try:
            data = [b.to_dict() for b in self._budgets.values()]
            self._budgets_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Could not save budgets: {e}")

    def set_budget(self, category: ExpenseCategory, allocated: Decimal, period: str = "monthly") -> BudgetCategory:
        budget = BudgetCategory(category=category.value, allocated=allocated, period=period)
        self._budgets[category.value] = budget
        self._save_budgets()
        return budget

    def get_budget(self, category: ExpenseCategory) -> BudgetCategory | None:
        return self._budgets.get(category.value)

    def get_all_budgets(self) -> list[BudgetCategory]:
        return list(self._budgets.values())

    def record_expense(self, category: ExpenseCategory, amount: Decimal) -> BudgetCategory | None:
        budget = self._budgets.get(category.value)
        if budget:
            budget.spent += amount
            self._save_budgets()
        return budget

    # ── Summaries ──
    def _load_summaries(self) -> None:
        try:
            if self._summaries_file.exists():
                data = json.loads(self._summaries_file.read_text())
                for raw in data:
                    self._summaries.append(
                        FinancialSummary(
                            period_start=raw["period_start"],
                            period_end=raw["period_end"],
                            total_income=Decimal(raw["total_income"]),
                            total_expenses=Decimal(raw["total_expenses"]),
                            net_income=Decimal(raw["net_income"]),
                            total_opportunities=raw["total_opportunities"],
                            completed_opportunities=raw["completed_opportunities"],
                            pending_opportunities=raw["pending_opportunities"],
                            total_work_hours=raw["total_work_hours"],
                            avg_profit_per_hour=raw["avg_profit_per_hour"],
                            top_platforms=raw.get("top_platforms", []),
                            top_categories=raw.get("top_categories", []),
                            savings_rate=raw.get("savings_rate", 0.0),
                        )
                    )
        except Exception as e:
            logger.warning(f"Could not load summaries: {e}")

    def _save_summaries(self) -> None:
        try:
            data = [s.to_dict() for s in self._summaries]
            self._summaries_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Could not save summaries: {e}")

    def add_summary(self, summary: FinancialSummary) -> FinancialSummary:
        self._summaries.append(summary)
        self._save_summaries()
        return summary

    def get_summaries(self, limit: int | None = None) -> list[FinancialSummary]:
        summaries = sorted(self._summaries, key=lambda s: s.period_start, reverse=True)
        if limit:
            return summaries[:limit]
        return summaries

    # ── Freedom Progress ──
    def _load_freedom_progress(self) -> None:
        try:
            if self._freedom_file.exists():
                data = json.loads(self._freedom_file.read_text())
                self._freedom_progress = FreedomProgress(
                    monthly_target=Decimal(data["monthly_target"]),
                    current_monthly_avg=Decimal(data["current_monthly_avg"]),
                    recurring_income=Decimal(data["recurring_income"]),
                    active_income_systems=data["active_income_systems"],
                    emergency_fund_months=data["emergency_fund_months"],
                    progress_pct=data["progress_pct"],
                    months_to_target=data["months_to_target"],
                    last_calculated=data["last_calculated"],
                )
        except Exception as e:
            logger.warning(f"Could not load freedom progress: {e}")

    def _save_freedom_progress(self) -> None:
        try:
            if self._freedom_progress:
                self._freedom_file.write_text(json.dumps(self._freedom_progress.to_dict(), indent=2))
        except Exception as e:
            logger.warning(f"Could not save freedom progress: {e}")

    def get_freedom_progress(self) -> FreedomProgress:
        if not self._freedom_progress:
            self._freedom_progress = FreedomProgress()
        return self._freedom_progress

    def update_freedom_progress(self, **kwargs) -> FreedomProgress:
        fp = self.get_freedom_progress()
        for k, v in kwargs.items():
            if hasattr(fp, k):
                setattr(fp, k, v)
        fp.last_calculated = datetime.now(UTC).isoformat()
        self._save_freedom_progress()
        return fp


_store: FinanceStore | None = None


def get_finance_store(store_dir: str | Path | None = None) -> FinanceStore:
    """Get the process-wide FinanceStore singleton."""
    global _store
    if _store is None:
        _store = FinanceStore(store_dir)
    return _store
