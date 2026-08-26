from __future__ import annotations

from cores.revenue.converter import calculate_fee, net_after_fee, usd_to_ars
from cores.revenue.models import Payment, RevenueRecord, RevenueStats
from cores.revenue.tracker import PaymentTracker

from cores.revenue.revenue_engine import RevenueEngine


def test_usd_to_ars():
    result = usd_to_ars(100, rate=1000)
    assert result == 100000


def test_net_after_fee():
    result = net_after_fee(100, "wise")
    assert result == 98.5


def test_calculate_fee():
    result = calculate_fee(100, "paypal")
    assert result == 4.5


def test_tracker_add_and_stats():
    tracker = PaymentTracker()
    record = RevenueRecord(
        id="rec_1",
        date="2026-07-29",
        source_type="bug_bounty",
        platform="hackerone",
        opportunity="Test vuln",
        reward_usd=200,
    )
    tracker.add_record(record)
    stats = tracker.get_stats(period_days=30)
    assert stats.total_usd == 200


def test_tracker_mark_paid():
    tracker = PaymentTracker()
    record = RevenueRecord(
        id="rec_2",
        date="2026-07-29",
        source_type="dev_bounty",
        platform="github",
        opportunity="Fix bug",
        reward_usd=50,
    )
    tracker.add_record(record)
    payment = Payment(
        id="pay_1",
        platform="github",
        opportunity_id="rec_2",
        amount_usd=50,
        status="pending",
        method="wise",
    )
    tracker.add_payment(payment)
    tracker.mark_paid("pay_1", method="wise")
    paid = tracker.get_payments_by_status("paid")
    assert len(paid) == 1


def test_revenue_engine_health():
    engine = RevenueEngine()
    health = engine.health()
    assert health["status"] == "ok"
    assert health["name"] == "revenue_engine"


def test_revenue_engine_methods():
    engine = RevenueEngine()
    methods = engine.available_methods()
    assert len(methods) == 5
    names = [m["name"] for m in methods]
    assert "wise" in names


def test_revenue_engine_discover():
    engine = RevenueEngine()
    from core.opportunity.models import ScoredOpportunity, UnifiedScore

    scored = [
        ScoredOpportunity(
            id="opp_1",
            name="Test Bounty",
            cycle="security",
            source_type="bug_bounty",
            source_name="HackerOne",
            reward=100,
            effort_hours=2,
            platform="hackerone",
            technology_tags=["python"],
            url=None,
            created_at="2026-07-29",
            score=UnifiedScore(overall=0.8),
        )
    ]
    results = engine.discover(scored, top_n=5)
    assert len(results) == 1
    assert results[0]["score_overall"] == 0.8


def test_revenue_engine_process_payment():
    engine = RevenueEngine()
    payment = engine.process_payment("opp_1", 100, "wise", "hackerone")
    assert payment.amount_usd == 100
    assert payment.method == "wise"


def test_revenue_stats_empty():
    stats = RevenueStats()
    d = stats.to_dict()
    assert d["total_usd"] == 0
    assert d["win_rate_pct"] == 0


def test_revenue_tracker_summary():
    tracker = PaymentTracker()
    summary = tracker.summary()
    assert "OWNEX Revenue Summary" in summary


def test_ar_get_payment_methods():
    from core.revenue.models import ARGENTINA_METHODS

    assert "wise" in ARGENTINA_METHODS
    assert "paypal" in ARGENTINA_METHODS
    assert "payoneer" in ARGENTINA_METHODS
    assert "cripto" in ARGENTINA_METHODS
    assert "transferencia" in ARGENTINA_METHODS
