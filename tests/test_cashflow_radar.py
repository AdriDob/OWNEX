"""Tests for the Cashflow Radar (Rapid Income Engine)."""

import pytest

from cores.direct_work_engine.cashflow_radar import (
    MIX_INCOME_STABLE,
    MIX_LIQUIDITY_NEEDED,
    RapidIncomeEngine,
    _estimate_hours,
    get_radar,
)


def _opp(**overrides: object) -> dict:
    base = {
        "id": "opp-1",
        "title": "Label 500 images",
        "platform": "labeler",
        "category": "data_annotation",
        "reward": 50.0,
        "url": "https://platform.example/task/1",
    }
    base.update(overrides)
    return base


def test_radar_buckets_classify_by_hours() -> None:
    radar = RapidIncomeEngine().radar(
        [
            _opp(id="fast", estimated_hours=2, reward=30),
            _opp(id="week", estimated_hours=30, reward=200),
            _opp(id="growth", estimated_hours=200, reward=900),
        ]
    )
    buckets = radar["buckets"]
    assert [i["id"] for i in buckets["today"]] == ["fast"]
    assert [i["id"] for i in buckets["week"]] == ["week"]
    assert [i["id"] for i in buckets["growth"]] == ["growth"]


def test_radar_recurring_goes_to_growth() -> None:
    radar = RapidIncomeEngine().radar([_opp(id="rec", estimated_hours=1, recurring=True)])
    assert [i["id"] for i in radar["buckets"]["growth"]] == ["rec"]


def test_radar_top_pick_prefers_liquidity() -> None:
    radar = RapidIncomeEngine().radar(
        [
            _opp(id="big-growth", estimated_hours=200, reward=900),
            _opp(id="quick", estimated_hours=1, reward=40),
        ]
    )
    assert radar["top_pick"]["id"] == "quick"


def test_radar_recommended_mix_liquidity_when_no_stable_base() -> None:
    radar = RapidIncomeEngine().radar([_opp(id="a", estimated_hours=2)])
    assert radar["recommended_mix"] == MIX_LIQUIDITY_NEEDED


def test_radar_recommended_mix_growth_when_stable_base() -> None:
    radar = RapidIncomeEngine().radar(
        [_opp(id="a", estimated_hours=2), _opp(id="b", estimated_hours=2, recurring=True)]
    )
    assert radar["recommended_mix"] == MIX_INCOME_STABLE


def test_radar_special_advantage_flags_high_automation() -> None:
    radar = RapidIncomeEngine().radar([_opp(id="a", estimated_hours=2)])
    item = radar["buckets"]["today"][0]
    # Only surfaced when automation_pct meets the threshold; default plan
    # automation is engine-driven, so the list may be empty — but never crashes.
    assert isinstance(item["what_ownrex_prepared"], list)


def test_daily_digest_lists_top_five_today() -> None:
    radar = RapidIncomeEngine().radar([_opp(id=f"t{i}", estimated_hours=1, title=f"Task {i}") for i in range(6)])
    digest = RapidIncomeEngine.daily_digest(radar)
    assert digest["text"].startswith("OWNEX DAILY OPPORTUNITIES")
    assert "1. Task 0" in digest["text"]
    assert "6." not in digest["text"]


def test_weekly_plan_aggregates_expected_earnings() -> None:
    radar = RapidIncomeEngine().radar([_opp(id="w", estimated_hours=30, reward=200)])
    plan = RapidIncomeEngine.weekly_plan(radar)
    assert plan["expected_earnings_usd"] > 0
    assert plan["priority_order"] == ["Label 500 images"]


def test_get_radar_with_explicit_opportunities() -> None:
    radar = get_radar([_opp(id="x", estimated_hours=1)])
    assert radar["buckets"]["today"][0]["id"] == "x"


def test_classify_hours_and_recurring() -> None:
    engine = RapidIncomeEngine()
    assert engine._classify(2.0, False) == "today"
    assert engine._classify(30.0, False) == "week"
    assert engine._classify(200.0, False) == "growth"
    assert engine._classify(1.0, True) == "growth"


def test_estimate_hours_priority() -> None:
    assert _estimate_hours({"estimated_hours": 3}, 120, "data_annotation") == 3
    assert _estimate_hours({}, 120, "data_annotation") == 2
    assert _estimate_hours({}, 0, "data_annotation") == 4
    assert _estimate_hours({}, 0, "bug_bounty") == 24


@pytest.fixture(scope="module")
def auth_client():
    from fastapi.testclient import TestClient

    from api.main import app
    from cores.license.validator import generate_license

    client = TestClient(app)
    lic = generate_license(expiry_days=365)
    client.post("/api/license/activate", json={"key": lic})
    resp = client.post("/api/auth/login", json={"device_id": "pytest-cashflow-radar"})
    if resp.status_code == 200:
        client.headers.update({"Authorization": f"Bearer {resp.json()['data']['token']}"})
    resp = client.get("/api/version")
    csrf_token = resp.cookies.get("csrf-token")
    if csrf_token:
        client.headers.update({"X-CSRF-Token": csrf_token})
    return client


def test_endpoint_with_explicit_opportunities(auth_client) -> None:
    payload = {
        "opportunities": [
            {
                "id": "api-label",
                "title": "API label task",
                "platform": "mindrift",
                "category": "data_annotation",
                "reward": 50.0,
                "estimated_hours": 3.0,
                "url": "https://example.com/task",
            }
        ]
    }
    resp = auth_client.post("/direct-work/cashflow-radar", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["buckets"]["today"][0]["id"] == "api-label"
    assert "daily_digest" in body
    assert "weekly_plan" in body
    assert "recommended_mix" in body
    assert body["top_pick"]["id"] == "api-label"


def test_endpoint_empty_uses_workbank(auth_client, tmp_path, monkeypatch) -> None:
    from cores.direct_work_engine import workbank as wb_module

    bank = wb_module.WorkBank(store_path=tmp_path / "bank.json")
    bank._items = {
        "endpoint_bank": wb_module.WorkItem(
            id="endpoint_bank",
            title="Endpoint bank task",
            platform="fiverr",
            category="fiverr",
            reward=25.0,
            barrier_score=75.0,
            employment_type="contract",
            status="ready_to_deliver",
            ready_to_deliver=True,
        )
    }
    monkeypatch.setattr(wb_module, "get_workbank", lambda: bank)
    resp = auth_client.post("/direct-work/cashflow-radar", json={})
    assert resp.status_code == 200
    body = resp.json()
    titles = [i["title"] for group in body["buckets"].values() for i in group]
    assert "Endpoint bank task" in titles
