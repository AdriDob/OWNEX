"""Tests for Finance module."""

from __future__ import annotations

from decimal import Decimal

import pytest

from cores.finance.engine import FinanceEngine
from cores.finance.models import (
    BudgetCategory,
    ExpenseCategory,
    FinancialAsset,
    FreedomProgress,
    Opportunity,
    Transaction,
    TransactionType,
    WorkIncomeRecord,
)
from cores.finance.store import FinanceStore


class TestFinanceModels:
    """Test finance data models."""

    def test_transaction_creation(self):
        txn = Transaction(
            amount=Decimal("100.50"),
            type=TransactionType.INCOME,
            category="freelance",
            description="Test payment",
            source="client_a",
        )
        assert txn.amount == Decimal("100.50")
        assert txn.type == TransactionType.INCOME
        assert txn.category == "freelance"

    def test_opportunity_creation(self):
        opp = Opportunity(
            title="Bug bounty",
            platform="hackerone",
            category="bounty",
            expected_reward=Decimal("500"),
            success_probability=0.3,
            human_time_hours=8.0,
        )
        assert opp.title == "Bug bounty"
        assert opp.platform == "hackerone"
        assert opp.ev_per_hour == (500 * 0.3) / 8.0

    def test_work_income_record(self):
        rec = WorkIncomeRecord(
            workbank_id="wb_123",
            platform="hackerone",
            title="Bug bounty",
            category="bounty",
            time_invested_hours=10.0,
            reward=Decimal("1000"),
            profit_per_hour=100.0,
        )
        assert rec.profit_per_hour == 100.0

    def test_budget_category(self):
        budget = BudgetCategory(
            category="food",
            allocated=Decimal("500"),
            spent=Decimal("300"),
        )
        assert budget.remaining == Decimal("200")
        assert budget.utilization_pct == 60.0

    def test_freedom_progress(self):
        fp = FreedomProgress(
            monthly_target=Decimal("5000"),
            current_monthly_avg=Decimal("2500"),
            progress_pct=50.0,
        )
        assert fp.progress_pct == 50.0

    def test_financial_asset(self):
        asset = FinancialAsset(
            name="Checking Account",
            type="bank",
            value=Decimal("10000"),
            currency="USD",
        )
        assert asset.value == Decimal("10000")


class TestFinanceStore:
    """Test finance store persistence."""

    @pytest.fixture
    def store(self, tmp_path):
        return FinanceStore(tmp_path / "finance")

    def test_transaction_crud(self, store):
        txn = Transaction(
            amount=Decimal("100"),
            type=TransactionType.INCOME,
            category="freelance",
            description="Test",
            source="client",
        )
        store.add_transaction(txn)

        retrieved = store.get_transaction(txn.id)
        assert retrieved is not None
        assert retrieved.amount == Decimal("100")

        all_txns = store.get_transactions()
        assert len(all_txns) == 1

        income_txns = store.get_income_transactions()
        assert len(income_txns) == 1

    def test_opportunity_crud(self, store):
        opp = Opportunity(
            title="Bug bounty",
            platform="hackerone",
            category="bounty",
            expected_reward=Decimal("500"),
            success_probability=0.3,
            human_time_hours=8.0,
        )
        store.add_opportunity(opp)

        retrieved = store.get_opportunity(opp.id)
        assert retrieved is not None
        assert retrieved.title == "Bug bounty"

        opps = store.get_opportunities()
        assert len(opps) == 1

    def test_work_income_crud(self, store):
        rec = WorkIncomeRecord(
            workbank_id="wb_1",
            platform="hackerone",
            title="Bug fix",
            category="bounty",
            time_invested_hours=5.0,
            reward=Decimal("250"),
            profit_per_hour=50.0,
        )
        store.add_work_income(rec)

        retrieved = store.get_work_income()
        assert len(retrieved) == 1
        assert retrieved[0].profit_per_hour == 50.0

    def test_budget_management(self, store):
        budget = store.set_budget(ExpenseCategory.FOOD, Decimal("500"))
        assert budget.allocated == Decimal("500")

        retrieved = store.get_budget(ExpenseCategory.FOOD)
        assert retrieved is not None

        store.record_expense(ExpenseCategory.FOOD, Decimal("100"))
        retrieved = store.get_budget(ExpenseCategory.FOOD)
        assert retrieved.spent == Decimal("100")

    def test_asset_management(self, store):
        asset = FinancialAsset(
            name="Savings",
            type="bank",
            value=Decimal("10000"),
        )
        store.add_asset(asset)

        assets = store.get_assets()
        assert len(assets) == 1
        assert store.get_total_assets_value() == Decimal("10000")

    def test_freedom_progress(self, store):
        fp = store.get_freedom_progress()
        assert fp.monthly_target == Decimal("5000")

        updated = store.update_freedom_progress(monthly_target=Decimal("10000"))
        assert updated.monthly_target == Decimal("10000")


class TestFinanceEngine:
    """Test finance intelligence engine."""

    @pytest.fixture
    def store(self, tmp_path):
        return FinanceStore(tmp_path / "finance")

    @pytest.fixture
    def engine(self, store):
        return FinanceEngine(store)

    def test_opportunity_ev_calculation(self, engine, store):
        opp = Opportunity(
            title="High EV bounty",
            platform="hackerone",
            category="bounty",
            expected_reward=Decimal("1000"),
            success_probability=0.5,
            human_time_hours=10.0,
        )
        store.add_opportunity(opp)

        ev = engine.calculate_opportunity_ev(opp)
        assert ev == 50.0  # (1000 * 0.5) / 10

    def test_rank_opportunities_by_ev(self, engine, store):
        opp1 = Opportunity(
            title="Low EV",
            platform="platform_a",
            category="bounty",
            expected_reward=Decimal("100"),
            success_probability=0.1,
            human_time_hours=10.0,
        )
        opp2 = Opportunity(
            title="High EV",
            platform="platform_b",
            category="bounty",
            expected_reward=Decimal("1000"),
            success_probability=0.5,
            human_time_hours=10.0,
        )
        store.add_opportunity(opp1)
        store.add_opportunity(opp2)

        ranked = engine.rank_opportunities_by_ev()
        assert ranked[0].title == "High EV"
        assert ranked[1].title == "Low EV"

    def test_get_top_opportunities(self, engine, store):
        for i in range(5):
            opp = Opportunity(
                title=f"Opp {i}",
                platform=f"platform_{i}",
                category="bounty",
                expected_reward=Decimal(str(100 * (i + 1))),
                success_probability=0.5,
                human_time_hours=10.0,
            )
            store.add_opportunity(opp)

        top = engine.get_top_opportunities(3)
        assert len(top) == 3
        assert top[0].title == "Opp 4"  # Highest reward

    def test_pipeline_summary(self, engine, store):
        for status in ["discovered", "evaluating", "in_progress", "completed", "paid"]:
            opp = Opportunity(
                title=f"Opp {status}",
                platform="test",
                category="bounty",
                expected_reward=Decimal("100"),
                status=status,
            )
            store.add_opportunity(opp)

        pipeline = engine.get_pipeline_summary()
        assert pipeline["discovered"] == 1
        assert pipeline["completed"] == 1
        assert pipeline["paid"] == 1

    def test_analyze_work_income(self, engine, store):
        for i in range(3):
            rec = WorkIncomeRecord(
                workbank_id=f"wb_{i}",
                platform="hackerone",
                title=f"Bounty {i}",
                category="bounty",
                time_invested_hours=10.0,
                reward=Decimal("500"),
                profit_per_hour=50.0,
            )
            store.add_work_income(rec)

        analysis = engine.analyze_work_income(30)
        assert analysis["total_records"] == 3
        assert analysis["total_reward"] == "1500"
        assert analysis["avg_profit_per_hour"] == 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
