"""MONEY VALIDATION instrumentation tests (OWNEX freeze: measure, don't build).

Covers the minimal instrumentation approved 2026-09-11:
- LearningRecord paid/net split (ACCEPTED != PAID) + tracker mapping
- channel_economy() personal empirical economy (PAID-only cash)
- WorkItem human-time tracking (START/DELIVER + manual correction)
- Payment rails tri-state + require_configured verdicts
- Fiverr funnel ledger (published -> withdrawn)
"""

from __future__ import annotations

from cores.direct_work_engine.evolution import channel_economy
from cores.direct_work_engine.feedback import LearningRecord, build_history_from_revenue_tracker
from cores.direct_work_engine.workbank import WorkBank, WorkItem
from cores.fiverr.engine import FUNNEL_STAGES, FunnelLedger
from cores.payment_compat.engine import PaymentRequirement, get_payment_engine


def _rec(platform: str, accepted: bool, amount: float = 0.0, **kw) -> LearningRecord:
    return LearningRecord(platform=platform, accepted=accepted, amount=amount, **kw)


# ── 1. ACCEPTED != PAID ──────────────────────────────────────────────────────


def test_paid_defaults_false() -> None:
    r = _rec("opire", True, 150.0)
    assert r.paid is False
    assert r.net_amount is None
    assert r.fees == 0.0


def test_build_history_maps_paid_status_to_cash() -> None:
    class _Opp:
        def __init__(self, status: str, amount: float, platform: str = "opire"):
            self.status = status
            self.amount = amount
            self.platform = platform

    class _Tracker:
        opportunities = {
            "a": _Opp("accepted", 200.0),
            "b": _Opp("paid", 150.0),
            "c": _Opp("failed", 0.0),
            "d": _Opp("pending", 99.0),
        }

    records = build_history_from_revenue_tracker(_Tracker())
    by_amount = {r.amount: r for r in records}
    assert by_amount[200.0].accepted is True
    assert by_amount[200.0].paid is False  # earned, NOT cash
    assert by_amount[150.0].paid is True
    assert by_amount[150.0].net_amount == 150.0
    assert 99.0 not in by_amount  # pending is not an outcome


# ── 2. channel_economy ───────────────────────────────────────────────────────


def test_channel_economy_unknown_without_paid() -> None:
    eco = channel_economy([_rec("opire", True, 150.0, actual_hours=4.0)])
    assert eco["verdict"] == "UNKNOWN"
    assert eco["totals"]["net_cash"] == 0.0
    assert eco["totals"]["net_per_hour"] is None


def test_channel_economy_measures_personal_truth() -> None:
    records = [
        _rec("opire", True, 150.0, paid=True, net_amount=135.0, actual_hours=6.0, time_to_payout_days=11.0),
        _rec("opire", True, 100.0, paid=True, net_amount=90.0, actual_hours=4.0, time_to_payout_days=9.0),
        _rec("opire", False, 0.0, actual_hours=3.0),
        _rec("fiverr", True, 80.0, paid=True, net_amount=72.0, actual_hours=5.0, time_to_payout_days=16.0),
    ]
    eco = channel_economy(records)
    assert eco["verdict"] == "MEASURED"
    opire = next(c for c in eco["channels"] if c["channel"] == "opire")
    assert opire["attempted"] == 3
    assert opire["accepted"] == 2
    assert opire["paid"] == 2
    assert opire["earned_gross"] == 250.0
    assert opire["net_cash"] == 225.0
    assert opire["human_hours"] == 13.0
    assert opire["net_per_hour"] == round(225.0 / 13.0, 2)
    assert opire["median_days_to_cash"] == 10.0
    assert eco["totals"]["net_cash"] == 297.0
    assert eco["totals"]["human_hours"] == 18.0


def test_channel_economy_thin_evidence() -> None:
    eco = channel_economy([_rec("opire", True, 50.0, paid=True, net_amount=45.0, actual_hours=2.0)])
    assert eco["verdict"] == "THIN_EVIDENCE"


# ── 3. WorkItem human time ───────────────────────────────────────────────────


def _item() -> WorkItem:
    return WorkItem(
        id="w1",
        title="t",
        platform="opire",
        category="dev_bounty",
        reward=100.0,
        barrier_score=80.0,
        employment_type="bounty",
    )


def test_work_item_time_defaults_none_legacy_safe() -> None:
    item = _item()
    assert item.started_at is None
    assert item.delivered_at is None
    assert item.human_minutes_actual is None
    # legacy JSON without the new keys still loads
    bank = WorkBank(store_path="/tmp/mv_workbank_legacy.json")
    bank._items = {}
    old = {
        "id": "old",
        "title": "t",
        "platform": "opire",
        "category": "dev_bounty",
        "reward": 50.0,
        "barrier_score": 70.0,
        "employment_type": "bounty",
    }
    bank._items["old"] = WorkItem(**old)
    assert bank._items["old"].human_minutes_actual is None


def test_mark_started_idempotent_and_delivered_stamps() -> None:
    bank = WorkBank(store_path="/tmp/mv_workbank_time.json")
    bank._items = {}
    item = _item()
    bank._items[item.id] = item
    item.mark_started()
    first = item.started_at
    assert first is not None
    item.mark_started()
    assert item.started_at == first
    assert bank.mark_delivered(item.id) is True
    assert item.delivered_at is not None


def test_record_human_minutes_validates() -> None:
    item = _item()
    assert item.record_human_minutes(37.5) is True
    assert item.human_minutes_actual == 37.5
    assert item.record_human_minutes(-5) is False
    assert item.human_minutes_actual == 37.5
    assert item.record_human_minutes("nope") is False  # type: ignore[arg-type]
    assert item.human_minutes_actual == 37.5


def test_mark_delivered_missing_returns_false() -> None:
    bank = WorkBank(store_path="/tmp/mv_workbank_miss.json")
    bank._items = {}
    assert bank.mark_delivered("nope") is False


# ── 4. Payment rails tri-state ───────────────────────────────────────────────


def test_account_status_tristate() -> None:
    engine = get_payment_engine()
    saved = engine.get_configured_accounts()
    try:
        engine.set_configured_accounts(["binance"])
        assert engine.account_status("binance") == "CONFIGURED"
        assert engine.account_status("kraken") == "NOT_CONFIGURED"
        assert engine.account_status("no_existe") == "UNVERIFIED"
    finally:
        get_payment_engine().set_configured_accounts(saved)


def test_require_configured_kills_theoretical_score() -> None:
    engine = get_payment_engine()
    saved = engine.get_configured_accounts()
    try:
        engine.set_configured_accounts([])
        req = PaymentRequirement(method="crypto", currency="USDC", region="global", amount=100.0)
        default = engine.evaluate(req)
        strict = engine.evaluate(req, require_configured=True)
        assert default.compatible is True  # catalog contract preserved
        assert strict.compatible is True  # route exists theoretically
        assert strict.viable is False
        assert strict.score == 0.0
        assert strict.configured_matches == 0
        assert any("configurada" in m for m in strict.missing)
    finally:
        get_payment_engine().set_configured_accounts(saved)


def test_require_configured_passes_with_real_rail() -> None:
    engine = get_payment_engine()
    saved = engine.get_configured_accounts()
    try:
        engine.set_configured_accounts(["binance"])
        req = PaymentRequirement(method="crypto", currency="USDC", region="global", amount=100.0)
        verdict = engine.evaluate(req, require_configured=True)
        assert verdict.viable is True
        assert verdict.score > 50
        assert verdict.configured_matches >= 1
        assert all(m.configured for m in verdict.matches if m.account_id == "binance")
    finally:
        get_payment_engine().set_configured_accounts(saved)


# ── 5. Fiverr funnel ─────────────────────────────────────────────────────────


def test_funnel_rejects_invalid_stage() -> None:
    ledger = FunnelLedger(store_path="/tmp/mv_funnel.json")
    assert ledger.record("gig1", "no_stage") is False
    assert ledger.record("", "orders") is False
    assert ledger.record("gig1", "orders", -2) is False


def test_funnel_summary_with_conversion() -> None:
    ledger = FunnelLedger(store_path="/tmp/mv_funnel2.json")
    ledger._counts = {}
    assert ledger.record("python_automation", "published") is True
    assert ledger.record("python_automation", "impressions", 430) is True
    assert ledger.record("python_automation", "clicks", 18) is True
    assert ledger.record("python_automation", "orders", 1) is True
    summary = ledger.summary("python_automation")
    gig = summary["gigs"]["python_automation"]
    assert gig["orders"] == 1
    assert gig["click_through_rate"] == round(18 / 430, 4)
    assert gig["order_conversion"] == round(1 / 18, 4)
    assert summary["stages"] == list(FUNNEL_STAGES)


# ── 6. Endpoints (visibility rule: if not visible, it does not exist) ─────────


def _authed_client():
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"device_id": "pytest-money-validation"})
    if resp.status_code == 200 and "data" in resp.json():
        client.headers.update({"Authorization": f"Bearer {resp.json()['data']['token']}"})
    csrf = resp.cookies.get("csrf_token") or resp.cookies.get("csrf")
    if csrf:
        client.headers.update({"X-CSRF-Token": csrf})
    return client


def test_payment_configured_endpoints() -> None:
    client = _authed_client()
    engine = get_payment_engine()
    saved = engine.get_configured_accounts()
    try:
        resp = client.post("/api/payment-compat/configured", json={"account_ids": ["binance"]})
        assert resp.status_code == 200
        assert resp.json()["configured_accounts"] == ["binance"]

        resp = client.get("/api/payment-compat/configured")
        assert resp.status_code == 200
        statuses = {s["id"]: s["status"] for s in resp.json()["statuses"]}
        assert statuses["binance"] == "CONFIGURED"
        assert statuses["kraken"] == "NOT_CONFIGURED"

        resp = client.post("/api/payment-compat/configured", json={"account_ids": ["nope"]})
        assert resp.status_code == 404

        resp = client.post(
            "/api/payment-compat/evaluate",
            json={"method": "crypto", "currency": "USDC", "region": "global", "require_configured": True},
        )
        assert resp.status_code == 200
        assert resp.json()["viable"] is True
        assert resp.json()["configured_matches"] >= 1
    finally:
        get_payment_engine().set_configured_accounts(saved)


def test_fiverr_funnel_endpoints() -> None:
    client = _authed_client()
    resp = client.post("/fiverr/funnel/record", json={"gig_key": "pytest_gig", "stage": "impressions", "count": 5})
    assert resp.status_code == 200
    assert resp.json()["recorded"] is True
    resp = client.post("/fiverr/funnel/record", json={"gig_key": "pytest_gig", "stage": "bogus"})
    assert resp.json()["recorded"] is False
    resp = client.get("/fiverr/funnel", params={"gig_key": "pytest_gig"})
    assert resp.status_code == 200
    assert resp.json()["gigs"]["pytest_gig"]["impressions"] >= 5


def test_evolution_includes_economy_and_access_has_configured() -> None:
    client = _authed_client()
    resp = client.post(
        "/direct-work/evolution",
        json={
            "profile": {"name": "Adriel", "country": "Argentina"},
            "records": [{"platform": "opire", "accepted": True, "amount": 100.0, "paid": True, "net_amount": 90.0}],
            "opportunities": [],
        },
    )
    assert resp.status_code == 200
    economy = resp.json()["economy"]
    assert economy["verdict"] == "THIN_EVIDENCE"
    assert economy["totals"]["net_cash"] == 90.0

    resp = client.get("/direct-work/access/explain")
    assert resp.status_code == 200
    platforms = {p["platform"]: p for p in resp.json()["platforms"]}
    assert platforms["opire"]["configured"] == "CONFIGURED"  # public tier
    assert platforms["hackerone"]["configured"] in ("CONFIGURED", "NOT_CONFIGURED", "UNVERIFIED")
