"""Tests for FinancialSyncScheduler earnings persistence with dedupe.

Ensures platform sync results are persisted to PayoutRecord correctly,
with external_id-based deduplication so capital dashboards grow from
real platform data without double-counting on every sync tick.
"""

from __future__ import annotations

from cores.financial.scheduler import FinancialSyncScheduler
from cores.platforms.base import SyncResult


class TestPersistEarnings:
    def test_persist_inserts_new_payouts(self, tmp_path) -> None:
        import os

        os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/test_payouts.db"
        from database.db import init_db

        init_db()

        sched = FinancialSyncScheduler()
        fake_result = SyncResult(
            success=True,
            earnings=[
                {
                    "id": "123",
                    "amount": 1500.0,
                    "currency": "USD",
                    "program": "h1",
                    "created_at": "2026-01-15T10:00:00Z",
                },
                {
                    "id": "124",
                    "amount": 2500.0,
                    "currency": "USD",
                    "program": "h1",
                    "created_at": "2026-01-16T10:00:00Z",
                },
            ],
            total_earned=4000.0,
            total_pending=0.0,
        )

        inserted, skipped = sched._persist_earnings("hackerone", fake_result)
        assert inserted == 2
        assert skipped == 0

        # Verify records in DB
        from database.db import SessionLocal
        from database.models_economic import PayoutRecord

        db = SessionLocal()
        rows = db.query(PayoutRecord).filter(PayoutRecord.platform == "hackerone").all()
        assert len(rows) == 2
        amounts = {r.amount for r in rows}
        assert amounts == {1500.0, 2500.0}
        external_ids = {r.external_id for r in rows}
        assert external_ids == {"hackerone:123", "hackerone:124"}
        for r in rows:
            assert r.status == "confirmed"
            assert r.currency == "USD"
            assert r.paid_at is not None
        db.close()

    def test_persist_deduplicates_on_second_call(self, tmp_path) -> None:
        import os

        os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/test_payouts2.db"
        from database.db import init_db

        init_db()

        sched = FinancialSyncScheduler()
        fake_result = SyncResult(
            success=True,
            earnings=[
                {
                    "id": "999",
                    "amount": 500.0,
                    "currency": "USD",
                    "program": "test",
                    "created_at": "2026-01-15T10:00:00Z",
                },
            ],
            total_earned=500.0,
            total_pending=0.0,
        )

        # First call - inserts
        inserted1, skipped1 = sched._persist_earnings("test_platform", fake_result)
        assert inserted1 == 1
        assert skipped1 == 0

        # Second call with SAME earning - should dedupe
        inserted2, skipped2 = sched._persist_earnings("test_platform", fake_result)
        assert inserted2 == 0
        assert skipped2 == 1

        # Verify only one row in DB
        from database.db import SessionLocal
        from database.models_economic import PayoutRecord

        db = SessionLocal()
        count = db.query(PayoutRecord).filter(PayoutRecord.platform == "test_platform").count()
        assert count == 1
        db.close()

    def test_persist_skips_earnings_without_id(self, tmp_path) -> None:
        import os

        os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/test_payouts3.db"
        from database.db import init_db

        init_db()

        sched = FinancialSyncScheduler()
        fake_result = SyncResult(
            success=True,
            earnings=[
                {"id": "", "amount": 100.0},  # empty id
                {"amount": 200.0},  # missing id
                {"id": "valid1", "amount": 300.0},
            ],
            total_earned=600.0,
            total_pending=0.0,
        )

        inserted, skipped = sched._persist_earnings("platform_x", fake_result)
        assert inserted == 1  # only the one with valid id
        assert skipped == 0

    def test_persist_handles_multiple_platforms_separately(self, tmp_path) -> None:
        import os

        os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/test_payouts4.db"
        from database.db import init_db

        init_db()

        sched = FinancialSyncScheduler()
        result_a = SyncResult(
            success=True, earnings=[{"id": "1", "amount": 100.0}], total_earned=100.0, total_pending=0.0
        )
        result_b = SyncResult(
            success=True, earnings=[{"id": "1", "amount": 200.0}], total_earned=200.0, total_pending=0.0
        )

        # Same external_id "platform_a:1" and "platform_b:1" should be different
        ia, sa = sched._persist_earnings("platform_a", result_a)
        ib, sb = sched._persist_earnings("platform_b", result_b)
        assert ia == 1 and ib == 1
        assert sa == 0 and sb == 0

        from database.db import SessionLocal
        from database.models_economic import PayoutRecord

        db = SessionLocal()
        a_rows = db.query(PayoutRecord).filter(PayoutRecord.platform == "platform_a").all()
        b_rows = db.query(PayoutRecord).filter(PayoutRecord.platform == "platform_b").all()
        assert len(a_rows) == 1
        assert len(b_rows) == 1
        assert a_rows[0].amount == 100.0
        assert b_rows[0].amount == 200.0
        db.close()

    def test_persist_empty_earnings_returns_zero(self, tmp_path) -> None:
        import os

        os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/test_payouts5.db"
        from database.db import init_db

        init_db()

        sched = FinancialSyncScheduler()
        fake_result = SyncResult(success=True, earnings=[], total_earned=0.0, total_pending=0.0)
        inserted, skipped = sched._persist_earnings("empty", fake_result)
        assert inserted == 0
        assert skipped == 0


class TestSyncPlatformsCallsPersist:
    def test_sync_platforms_returns_results_dict(self) -> None:
        sched = FinancialSyncScheduler()
        # Without credentials, it returns empty dict (skip all)
        results = sched.sync_platforms()
        assert isinstance(results, dict)
