"""Command Center contract tests — P1 AI-native Command Center.

Covers the DEFINITIVE §11/§25 next-action contract:
  WHY + RISK + SUCCESS_CONDITION + NEXT on every recommendation,
  estimated money is null (never fabricated) unless computed from
  recorded data, and semantics labeled FACT/INFERENCE/RECOMMENDATION/UNKNOWN.
"""

from __future__ import annotations

import pytest

from api.routers import command_center as cc


@pytest.fixture
def fresh_loop(monkeypatch):
    """Isolated revenue loop so tests never touch global/persisted state."""
    from cores.learning.revenue_loop import RevenueLearningLoop

    loop = RevenueLearningLoop()
    monkeypatch.setattr(
        "cores.learning.revenue_loop.get_revenue_loop",
        lambda: loop,
    )
    # command_center imports get_revenue_loop lazily from the same module,
    # so patching the module attribute is sufficient.
    return loop


@pytest.mark.asyncio
async def test_next_action_from_pending_uses_recorded_ev(fresh_loop):
    """Pending path: EV comes from the recorded action (computed, not invented)."""
    fresh_loop.record_action(
        opportunity_id="opp_1",
        action_type="investigate",
        title="Investigate example.com",
        description="Recon",
        human_minutes=30,
        expected_value=200,
    )

    action = await cc._get_next_action()

    assert action["opportunity_id"] == "opp_1"
    assert action["expected_value"] == 200
    assert action["ev_per_hour"] == 400.0
    assert action["why"].startswith("Highest expected value per hour")
    assert action["risk"] == "unknown"
    assert action["success_condition"] == "Recon report complete with attack surface mapped"
    assert action["next"] == "Open opp_1"
    sem = action["semantics"]
    assert sem["FACT"] and sem["INFERENCE"] and sem["RECOMMENDATION"]
    assert "Success probability" in sem["UNKNOWN"]


@pytest.mark.asyncio
async def test_next_action_empty_state_is_honest(fresh_loop):
    """Empty loop + empty DB: NO ACTION REQUIRED, nothing fabricated."""
    action = await cc._get_next_action()

    assert action["action_type"] == "none"
    assert action["opportunity_id"] is None
    assert action["expected_value"] == 0
    assert action["why"] == "No pending actions and no active targets found"
    assert action["semantics"]["RECOMMENDATION"] == []


@pytest.mark.asyncio
async def test_next_action_unscored_target_marks_unknown(fresh_loop):
    """Unscored-target fallback: real context counts, EV explicitly null."""
    from database import db, models

    db.init_db()
    session = db.SessionLocal()
    try:
        target = models.Target(name="unscored.example.com", domain="unscored.example.com", active=True)
        session.add(target)
        session.commit()
        tid = target.id
    finally:
        session.close()

    try:
        action = await cc._get_next_action()
    finally:
        session = db.SessionLocal()
        try:
            session.query(models.Target).filter(models.Target.id == tid).delete()
            session.commit()
        finally:
            session.close()

    assert action["action_type"] == "investigate"
    assert str(action["opportunity_id"]).startswith("target_")
    # Estimated money must be null here — the fallback never scores.
    assert action["expected_value"] is None
    assert action["ev_per_hour"] is None
    assert "not yet scored" in action["why"]
    assert "Expected value" in action["semantics"]["UNKNOWN"]
    # Context counts must match the picked target's real rows.
    picked_tid = int(str(action["opportunity_id"]).split("_", 1)[1])
    session = db.SessionLocal()
    try:
        ep_count = session.query(models.Endpoint).filter(models.Endpoint.target_id == picked_tid).count()
        f_count = session.query(models.Finding).filter(models.Finding.target_id == picked_tid).count()
    finally:
        session.close()
    assert any(f"{ep_count} endpoint(s)" in f for f in action["semantics"]["FACT"])
    assert any(f"{f_count} finding(s)" in f for f in action["semantics"]["FACT"])


def test_ai_status_never_raises_and_uses_fixed_vocabulary():
    """AI status degrades gracefully; status is always a known value."""
    status = cc._get_ai_status()

    assert status["status"] in ("operational", "degraded", "unavailable")
    for key in (
        "healthy_providers",
        "degraded_providers",
        "unhealthy_providers",
        "daily_spent_usd",
        "daily_budget_usd",
        "budget_exceeded",
    ):
        assert key in status
    assert isinstance(status["daily_spent_usd"], (int, float))
    assert isinstance(status["budget_exceeded"], bool)


def test_success_conditions_cover_known_action_types():
    for action_type in ("investigate", "submit", "approve", "review", "something_new"):
        condition = cc._success_condition(action_type)
        assert isinstance(condition, str) and condition


@pytest.fixture()
def clean_ledger():
    """Isolated revenue_ledger table for tier tests."""
    from cores.revenue.ledger import RevenueLedgerEntry
    from database.db import Base, engine

    Base.metadata.drop_all(bind=engine, tables=[RevenueLedgerEntry.__table__])
    Base.metadata.create_all(bind=engine, tables=[RevenueLedgerEntry.__table__])
    yield
    Base.metadata.drop_all(bind=engine, tables=[RevenueLedgerEntry.__table__])


def _drive_to_paid(ledger, entry_id: str, gross: float, fees: float = 0.0):
    """Walk an entry through the full valid chain to PAID."""
    from cores.revenue.ledger import RevenueState

    ledger.create(entry_id, gross_usd=gross)
    for state in (
        RevenueState.COMMITTED,
        RevenueState.IN_PROGRESS,
        RevenueState.DELIVERED,
        RevenueState.SUBMITTED,
        RevenueState.ACCEPTED,
        RevenueState.AWARDED,
        RevenueState.PENDING_PAYOUT,
        RevenueState.PAID,
    ):
        kwargs = {"fees_usd": fees} if state == RevenueState.PAID else {}
        entry = ledger.transition(entry_id, state, **kwargs)
        assert entry is not None
    return entry


@pytest.mark.asyncio
async def test_tiers_empty_state_is_honest(clean_ledger):
    """No ledger rows: zeros everywhere, survival not met, no invention."""
    tiers = await cc.get_tiers()

    assert tiers["realized_mtd_net_usd"] == 0
    assert tiers["pending_usd"] == 0
    assert tiers["tiers"]["survival"]["met"] is False
    assert tiers["tiers"]["target"]["target_usd"] == 5000.0
    assert tiers["tiers"]["target"]["on_track"] is False
    assert tiers["tiers"]["stretch"]["target_usd"] == 15000.0
    assert tiers["projection_monthly_usd"] == 0
    assert tiers["semantics"]["FACT"]


@pytest.mark.asyncio
async def test_tiers_counts_only_paid_net_mtd(clean_ledger):
    """A $1,000 PAID entry (10% fees) counts $900 realized, not $1,000."""
    from cores.revenue.ledger import get_revenue_ledger

    ledger = get_revenue_ledger()
    _drive_to_paid(ledger, "tier_test_1", gross=1000.0, fees=100.0)

    tiers = await cc.get_tiers()

    assert tiers["realized_mtd_net_usd"] == 900.0
    assert tiers["tiers"]["survival"]["met"] is True
    # Pace scales the $900 over elapsed month days — positive but finite.
    assert tiers["pace_monthly_usd"] > 900.0
    assert tiers["tiers"]["target"]["gap_usd"] == round(max(5000.0 - tiers["pace_monthly_usd"], 0.0), 2)


@pytest.mark.asyncio
async def test_tiers_accept_custom_targets(clean_ledger):
    """Target/stretch thresholds are caller-configurable."""
    tiers = await cc.get_tiers(target=1000.0, stretch=3000.0)

    assert tiers["tiers"]["target"]["target_usd"] == 1000.0
    assert tiers["tiers"]["stretch"]["target_usd"] == 3000.0
