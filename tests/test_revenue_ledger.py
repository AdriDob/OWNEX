"""Tests for Revenue Ledger."""

from __future__ import annotations

import pytest

from core.revenue.ledger import (
    RevenueLedger,
    RevenueLedgerEntry,
    RevenueState,
    RevenueTransition,
)


@pytest.fixture()
def clean_ledger():
    """Provide a clean revenue ledger for each test."""
    from database.db import Base, engine

    # Drop and recreate tables
    Base.metadata.drop_all(bind=engine, tables=[RevenueLedgerEntry.__table__])
    Base.metadata.create_all(bind=engine, tables=[RevenueLedgerEntry.__table__])

    ledger = RevenueLedger()
    yield ledger

    # Cleanup
    Base.metadata.drop_all(bind=engine, tables=[RevenueLedgerEntry.__table__])


class TestRevenueLedger:
    """Tests for RevenueLedger."""

    def test_create_entry(self, clean_ledger):
        """Test creating a revenue entry."""
        entry = clean_ledger.create(
            entry_id="test_entry_1",
            mission_id="mission-1",
            opportunity_id="opp-1",
            platform="hackerone",
            gross_usd=1000.0,
            fees_usd=50.0,
            fx_usd=10.0,
            tax_estimate_usd=100.0,
            payment_method="wire",
            external_id="ext-123",
            metadata={"source": "test"},
        )
        assert entry.entry_id == "test_entry_1"
        assert entry.mission_id == "mission-1"
        assert entry.state == "discovered"
        assert entry.gross_usd == 1000.0
        assert entry.fees_usd == 50.0
        assert entry.net_usd == 840.0  # 1000 - 50 - 10 - 100

    def test_get_entry(self, clean_ledger):
        """Test retrieving an entry by ID."""
        clean_ledger.create(entry_id="test_entry_2", mission_id="mission-2")
        entry = clean_ledger.get("test_entry_2")
        assert entry is not None
        assert entry.entry_id == "test_entry_2"
        assert entry.mission_id == "mission-2"

    def test_transition_valid(self, clean_ledger):
        """Test valid state transition."""
        clean_ledger.create(entry_id="test_entry_3", mission_id="mission-3", gross_usd=500.0)

        # DISCOVERED -> COMMITTED
        entry = clean_ledger.transition("test_entry_3", "committed")
        assert entry is not None
        assert entry.state == "committed"
        assert entry.previous_state == "discovered"

        # COMMITTED -> IN_PROGRESS
        entry = clean_ledger.transition("test_entry_3", "in_progress")
        assert entry.state == "in_progress"

        # IN_PROGRESS -> DELIVERED
        entry = clean_ledger.transition("test_entry_3", "delivered")
        assert entry.state == "delivered"

        # DELIVERED -> SUBMITTED
        entry = clean_ledger.transition("test_entry_3", "submitted")
        assert entry.state == "submitted"

        # SUBMITTED -> ACCEPTED
        entry = clean_ledger.transition("test_entry_3", "accepted")
        assert entry.state == "accepted"

        # ACCEPTED -> AWARDED
        entry = clean_ledger.transition("test_entry_3", "awarded")
        assert entry.state == "awarded"

        # AWARDED -> PENDING_PAYOUT
        entry = clean_ledger.transition("test_entry_3", "pending_payout")
        assert entry.state == "pending_payout"

        # PENDING_PAYOUT -> PAID
        entry = clean_ledger.transition("test_entry_3", "paid")
        assert entry.state == "paid"

        # PAID -> NET
        entry = clean_ledger.transition("test_entry_3", "net")
        assert entry.state == "net"

    def test_transition_invalid(self, clean_ledger):
        """Test invalid state transition is rejected."""
        clean_ledger.create(entry_id="test_entry_4", mission_id="mission-4")
        # DISCOVERED -> AWARDED (invalid, skips stages)
        entry = clean_ledger.transition("test_entry_4", "awarded")
        assert entry is None  # Should be rejected

    def test_transition_with_financials(self, clean_ledger):
        """Test transition with financial updates."""
        clean_ledger.create(entry_id="test_entry_5", mission_id="mission-5", gross_usd=1000.0)
        clean_ledger.transition("test_entry_5", "committed")
        clean_ledger.transition("test_entry_5", "in_progress")
        clean_ledger.transition("test_entry_5", "delivered")
        clean_ledger.transition("test_entry_5", "submitted")
        clean_ledger.transition("test_entry_5", "accepted")
        clean_ledger.transition("test_entry_5", "awarded")
        clean_ledger.transition("test_entry_5", "pending_payout")

        # Record payout with fees
        entry = clean_ledger.record_payout(
            "test_entry_5",
            amount_usd=500.0,
            payment_method="wire",
            external_id="payout-123",
            fees_usd=25.0,
            fx_usd=5.0,
            tax_estimate_usd=50.0,
        )
        assert entry is not None
        assert entry.state == "paid"
        assert entry.fees_usd == 25.0
        assert entry.fx_usd == 5.0
        assert entry.tax_estimate_usd == 50.0
        # net = gross - fees - fx - tax = 1000 - 25 - 5 - 50 = 920
        assert entry.net_usd == 920.0

    def test_get_by_mission(self, clean_ledger):
        """Test getting entries by mission."""
        clean_ledger.create(entry_id="e1", mission_id="mission-A")
        clean_ledger.create(entry_id="e2", mission_id="mission-A")
        clean_ledger.create(entry_id="e3", mission_id="mission-B")

        entries = clean_ledger.get_by_mission("mission-A")
        assert len(entries) == 2
        assert all(e.mission_id == "mission-A" for e in entries)

    def test_get_by_platform(self, clean_ledger):
        """Test getting entries by platform."""
        clean_ledger.create(entry_id="e1", platform="hackerone")
        clean_ledger.create(entry_id="e2", platform="bugcrowd")
        clean_ledger.create(entry_id="e3", platform="hackerone")

        entries = clean_ledger.get_by_platform("hackerone")
        assert len(entries) == 2
        assert all(e.platform == "hackerone" for e in entries)

    def test_get_by_state(self, clean_ledger):
        """Test getting entries by state."""
        clean_ledger.create(entry_id="e1")
        clean_ledger.create(entry_id="e2")
        clean_ledger.transition("e2", "committed")

        discovered = clean_ledger.get_by_state("discovered")
        committed = clean_ledger.get_by_state("committed")

        assert len(discovered) >= 1
        assert len(committed) >= 1

    def test_pending_payouts(self, clean_ledger):
        """Test getting pending payouts."""
        clean_ledger.create(entry_id="e1")
        clean_ledger.create(entry_id="e2")
        clean_ledger.transition("e2", "committed")
        clean_ledger.transition("e2", "in_progress")
        clean_ledger.transition("e2", "delivered")
        clean_ledger.transition("e2", "submitted")
        clean_ledger.transition("e2", "accepted")
        clean_ledger.transition("e2", "awarded")
        clean_ledger.transition("e2", "pending_payout")

        pending = clean_ledger.get_pending_payouts()
        assert len(pending) >= 1
        assert all(e.state == "pending_payout" for e in pending)

    def test_paid_entries(self, clean_ledger):
        """Test getting paid entries."""
        clean_ledger.create(entry_id="e1")
        clean_ledger.create(entry_id="e2")
        # e2 goes all the way to PAID
        for state in [
            "committed",
            "in_progress",
            "delivered",
            "submitted",
            "accepted",
            "awarded",
            "pending_payout",
            "paid",
        ]:
            clean_ledger.transition("e2", state)

        paid = clean_ledger.get_paid_entries()
        assert len(paid) >= 1
        assert all(e.state == "paid" for e in paid)

    def test_summary(self, clean_ledger):
        """Test revenue summary."""
        clean_ledger.create(entry_id="s1", gross_usd=1000.0, fees_usd=50.0, fx_usd=10.0, tax_estimate_usd=100.0)
        clean_ledger.create(entry_id="s2", gross_usd=500.0, fees_usd=25.0, fx_usd=5.0, tax_estimate_usd=50.0)

        summary = clean_ledger.get_summary()
        assert summary["total_gross_usd"] == 1500.0
        assert summary["total_fees_usd"] == 75.0
        assert summary["total_fx_usd"] == 15.0
        assert summary["total_tax_estimate_usd"] == 150.0
        assert summary["total_net_usd"] == 1260.0  # 1500 - 75 - 15 - 150 = 1260
        assert "discovered" in summary["by_state"]


class TestRevenueTransition:
    """Tests for RevenueTransition validation."""

    def test_valid_transitions(self):
        """Test all valid transitions."""
        assert RevenueTransition.is_valid(RevenueState.DISCOVERED, RevenueState.COMMITTED)
        assert RevenueTransition.is_valid(RevenueState.COMMITTED, RevenueState.IN_PROGRESS)
        assert RevenueTransition.is_valid(RevenueState.IN_PROGRESS, RevenueState.DELIVERED)
        assert RevenueTransition.is_valid(RevenueState.DELIVERED, RevenueState.SUBMITTED)
        assert RevenueTransition.is_valid(RevenueState.SUBMITTED, RevenueState.ACCEPTED)
        assert RevenueTransition.is_valid(RevenueState.ACCEPTED, RevenueState.AWARDED)
        assert RevenueTransition.is_valid(RevenueState.AWARDED, RevenueState.PENDING_PAYOUT)
        assert RevenueTransition.is_valid(RevenueState.PENDING_PAYOUT, RevenueState.PAID)
        assert RevenueTransition.is_valid(RevenueState.PAID, RevenueState.NET)

    def test_invalid_transitions(self):
        """Test invalid transitions are rejected."""
        assert not RevenueTransition.is_valid(RevenueState.DISCOVERED, RevenueState.AWARDED)
        assert not RevenueTransition.is_valid(RevenueState.COMMITTED, RevenueState.PAID)
        assert not RevenueTransition.is_valid(RevenueState.ACCEPTED, RevenueState.DISCOVERED)
        assert not RevenueTransition.is_valid(RevenueState.PAID, RevenueState.COMMITTED)

    def test_backwards_transitions_allowed(self):
        """Some backwards transitions are allowed for retries."""
        assert RevenueTransition.is_valid(RevenueState.COMMITTED, RevenueState.DISCOVERED)
        assert RevenueTransition.is_valid(RevenueState.IN_PROGRESS, RevenueState.COMMITTED)
        assert RevenueTransition.is_valid(RevenueState.DELIVERED, RevenueState.IN_PROGRESS)
        assert RevenueTransition.is_valid(RevenueState.SUBMITTED, RevenueState.DELIVERED)
        assert RevenueTransition.is_valid(RevenueState.ACCEPTED, RevenueState.SUBMITTED)
        assert RevenueTransition.is_valid(RevenueState.REJECTED, RevenueState.SUBMITTED)
        assert RevenueTransition.is_valid(RevenueState.AWARDED, RevenueState.ACCEPTED)
        assert RevenueTransition.is_valid(RevenueState.PENDING_PAYOUT, RevenueState.AWARDED)
        assert RevenueTransition.is_valid(RevenueState.PAID, RevenueState.PENDING_PAYOUT)


class TestRevenueLedgerIntegration:
    """Integration tests for full revenue lifecycle."""

    def test_full_lifecycle(self, clean_ledger):
        """Test complete revenue lifecycle from discovery to net."""
        entry = clean_ledger.create(
            entry_id="lifecycle-1",
            mission_id="mission-lifecycle",
            opportunity_id="opp-1",
            platform="hackerone",
            gross_usd=2000.0,
            fees_usd=100.0,
            fx_usd=20.0,
            tax_estimate_usd=200.0,
        )
        assert entry.state == "discovered"
        assert entry.net_usd == 1680.0  # 2000 - 100 - 20 - 200

        # Progress through all stages
        stages = [
            "committed",
            "in_progress",
            "delivered",
            "submitted",
            "accepted",
            "awarded",
            "pending_payout",
            "paid",
            "net",
        ]

        for i, stage in enumerate(stages):
            entry = clean_ledger.transition(entry.entry_id, stage)
            assert entry is not None, f"Failed at stage {stage}"
            assert entry.state == stage

        # Final state should be NET
        final_entry = clean_ledger.get(entry.entry_id)
        assert final_entry.state == "net"
        # Net should account for all fees
        assert final_entry.net_usd == 1680.0

    def test_revenue_ledger_summary(self, clean_ledger):
        """Test summary aggregates correctly."""
        clean_ledger.create(entry_id="s1", gross_usd=1000.0, fees_usd=50.0, fx_usd=10.0, tax_estimate_usd=100.0)
        clean_ledger.create(entry_id="s2", gross_usd=500.0, fees_usd=25.0, fx_usd=5.0, tax_estimate_usd=50.0)

        summary = clean_ledger.get_summary()
        assert summary["total_gross_usd"] == 1500.0
        assert summary["total_fees_usd"] == 75.0
        assert summary["total_fx_usd"] == 15.0
        assert summary["total_tax_estimate_usd"] == 150.0
        assert summary["total_net_usd"] == 1260.0  # 1500 - 75 - 15 - 150 = 1260
