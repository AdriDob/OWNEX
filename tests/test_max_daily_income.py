"""Tests del OWNEX MAX DAILY INCOME — plan de ejecución diaria con EV honesto."""

from __future__ import annotations

import pytest

from cores.direct_work_engine.max_daily_income import (
    CASH_SPEED_FACTORS,
    DEFAULT_DAILY_TARGET,
    MaxDailyIncomeEngine,
    get_max_daily_plan,
)


def _opp(category: str, reward: float, title: str = "job", blocked: bool = False) -> dict:
    return {
        "platform": "test",
        "title": title,
        "category": category,
        "reward": reward,
        "needs_access": blocked,
        "direct_link": "https://example.com/job",
    }


def test_plan_shape() -> None:
    plan = MaxDailyIncomeEngine().plan(opportunities=[], daily_target_usd=0.0)
    for key in (
        "generated_at",
        "daily_target_usd",
        "conservative_max_usd",
        "realistic_max_usd",
        "optimistic_max_usd",
        "unlock_potential_usd",
        "gap_usd",
        "optimism_arguments",
        "items",
        "needs_access_count",
        "actions",
        "notes",
        "digest",
    ):
        assert key in plan


def test_bug_bounty_not_ranked_as_today() -> None:
    plan = MaxDailyIncomeEngine().plan(
        opportunities=[_opp("bug_bounty", 5000.0, "bounty"), _opp("data_annotation", 50.0, "microtask")],
        daily_target_usd=0.0,
    )
    by_title = {i["title"]: i for i in plan["items"]}
    assert by_title["bounty"]["cash_window"] == "colas"
    assert by_title["bounty"]["cash_speed"] == 0.25
    assert by_title["bounty"]["expected_value_usd"] == pytest.approx(
        by_title["bounty"]["reward"] * by_title["bounty"]["probability_full"] * 0.25
    )
    assert by_title["bounty"]["expected_value_usd"] < by_title["bounty"]["reward"]
    assert by_title["bounty"]["probability_full"] <= 0.45
    assert plan["realistic_max_usd"] == pytest.approx(by_title["microtask"]["expected_value_usd"])


def test_data_annotation_is_cobrable_hoy() -> None:
    plan = MaxDailyIncomeEngine().plan(
        opportunities=[_opp("data_annotation", 50.0, "microtask")],
        daily_target_usd=0.0,
    )
    item = plan["items"][0]
    assert item["cash_window"] == "hoy"
    assert item["cash_speed"] == 1.0
    assert item["probability_full"] >= item["probability_base"]
    assert plan["realistic_max_usd"] == pytest.approx(item["expected_value_usd"])


def test_three_ceilings_ordered() -> None:
    plan = MaxDailyIncomeEngine().plan(
        opportunities=[
            _opp("data_annotation", 50.0, "ok", blocked=False),
            _opp("data_annotation", 200.0, "blocked", blocked=True),
        ],
        daily_target_usd=0.0,
    )
    assert plan["conservative_max_usd"] <= plan["realistic_max_usd"] <= plan["optimistic_max_usd"]
    by_title = {i["title"]: i for i in plan["items"]}
    assert plan["unlock_potential_usd"] == pytest.approx(by_title["blocked"]["expected_value_usd"])
    assert plan["optimistic_max_usd"] == pytest.approx(plan["realistic_max_usd"] + plan["unlock_potential_usd"])


def test_blocked_jobs_excluded_from_ceiling() -> None:
    plan = MaxDailyIncomeEngine().plan(
        opportunities=[
            _opp("data_annotation", 50.0, "ok", blocked=False),
            _opp("data_annotation", 200.0, "blocked", blocked=True),
        ],
        daily_target_usd=0.0,
    )
    assert plan["needs_access_count"] == 1
    by_title = {i["title"]: i for i in plan["items"]}
    assert plan["realistic_max_usd"] == pytest.approx(by_title["ok"]["expected_value_usd"])
    assert any("configurar accesos" in a for a in plan["actions"])


def test_optimism_arguments_backed_by_data() -> None:
    plan = MaxDailyIncomeEngine().plan(
        opportunities=[
            _opp("data_annotation", 50.0, "microtask"),
            _opp("data_annotation", 200.0, "blocked", blocked=True),
        ],
        daily_target_usd=40.0,
    )
    assert plan["optimism_arguments"]
    assert any("aceptación post-plan" in a for a in plan["optimism_arguments"])
    assert any("desbloquear" in a for a in plan["optimism_arguments"])
    assert any("alcanzable" in a for a in plan["optimism_arguments"])


def test_gap_vs_target() -> None:
    plan = MaxDailyIncomeEngine().plan(
        opportunities=[_opp("data_annotation", 50.0)],
        daily_target_usd=500.0,
    )
    assert plan["daily_target_usd"] == 500.0
    assert plan["gap_usd"] > 0
    assert plan["gap_usd"] == pytest.approx(500.0 - plan["optimistic_max_usd"])


def test_zero_target_reports_ceiling_only() -> None:
    plan = MaxDailyIncomeEngine().plan(opportunities=[], daily_target_usd=0.0)
    assert plan["daily_target_usd"] == 0.0
    assert plan["gap_usd"] == 0.0
    assert any("meta diaria" in n for n in plan["notes"])


def test_ranking_by_expected_value() -> None:
    plan = MaxDailyIncomeEngine().plan(
        opportunities=[
            _opp("data_annotation", 30.0, "a"),
            _opp("data_annotation", 90.0, "b"),
            _opp("data_annotation", 60.0, "c"),
        ],
        daily_target_usd=0.0,
    )
    evs = [i["expected_value_usd"] for i in plan["items"]]
    assert evs == sorted(evs, reverse=True)
    assert plan["items"][0]["title"] == "b"


def test_zero_reward_skipped() -> None:
    plan = MaxDailyIncomeEngine().plan(
        opportunities=[_opp("data_annotation", 0.0), _opp("data_annotation", 10.0, "real")],
        daily_target_usd=0.0,
    )
    assert all(i["title"] == "real" for i in plan["items"])


def test_digest_format() -> None:
    plan = MaxDailyIncomeEngine().plan(
        opportunities=[_opp("data_annotation", 50.0, "microtask")],
        daily_target_usd=100.0,
    )
    text = plan["digest"]["text"]
    assert text.startswith("OWNEX MAX DAILY INCOME")
    assert "Daily target: $100.0" in text
    assert "Optimistic ceiling" in text
    assert "Realistic ceiling" in text
    assert "Conservative floor" in text
    assert "Argumentos de optimismo" in text
    assert "Top pick: microtask" in text


def test_optimistic_ceiling_presented_first() -> None:
    plan = MaxDailyIncomeEngine().plan(
        opportunities=[_opp("data_annotation", 50.0, "microtask")],
        daily_target_usd=100.0,
    )
    text = plan["digest"]["text"]
    assert text.index("Optimistic ceiling") < text.index("Realistic ceiling")
    assert text.index("Realistic ceiling") < text.index("Conservative floor")


def test_empty_plan_is_honest() -> None:
    plan = MaxDailyIncomeEngine().plan(opportunities=[], daily_target_usd=100.0)
    assert plan["realistic_max_usd"] == 0.0
    assert "Top pick: ninguno" in plan["digest"]["text"]
    assert any("sin trabajo cobrable" in n for n in plan["notes"])


def test_target_persisted_and_loaded(monkeypatch) -> None:
    saved: list[tuple] = []

    class FakeMemory:
        def store(self, namespace, key, content, tags=None, priority=1.0):
            saved.append((namespace, key, content))

        def get(self, namespace, key):
            if saved:
                ns, k, content = saved[-1]
                return {"content": content}
            return None

    import cores.direct_work_engine.max_daily_income as mdi

    monkeypatch.setattr(mdi, "_load_target", lambda: float(saved[-1][2]) if saved else DEFAULT_DAILY_TARGET)
    monkeypatch.setattr(
        "cores.direct_work_engine.max_daily_income._save_target",
        lambda t: FakeMemory().store("user", "daily_income_target", str(t)),
    )
    get_max_daily_plan(opportunities=[], daily_target_usd=250.0)
    assert saved and saved[-1][2] == "250.0"
    plan = MaxDailyIncomeEngine().plan(opportunities=[], daily_target_usd=None)
    assert plan["daily_target_usd"] == 250.0


def test_cash_speed_factors_cover_fast_categories() -> None:
    for cat in ("data_annotation", "ai_training", "fiverr", "web_scraping"):
        assert CASH_SPEED_FACTORS[cat] >= 0.85
    assert CASH_SPEED_FACTORS["bug_bounty"] < 0.4


@pytest.fixture(scope="module")
def auth_client():
    from fastapi.testclient import TestClient

    from api.main import app
    from cores.license.validator import generate_license

    client = TestClient(app)
    lic = generate_license(expiry_days=365)
    client.post("/api/license/activate", json={"key": lic})
    resp = client.post("/api/auth/login", json={"device_id": "pytest-max-daily"})
    if resp.status_code == 200:
        client.headers.update({"Authorization": f"Bearer {resp.json()['data']['token']}"})
    resp = client.get("/api/version")
    csrf_token = resp.cookies.get("csrf-token")
    if csrf_token:
        client.headers.update({"X-CSRF-Token": csrf_token})
    return client


def test_max_daily_income_endpoint(auth_client) -> None:
    resp = auth_client.post(
        "/direct-work/max-daily-income",
        json={"opportunities": [_opp("data_annotation", 40.0, "microtask")], "daily_target_usd": 200.0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["daily_target_usd"] == 200.0
    assert body["items"][0]["cash_window"] == "hoy"
    assert body["optimistic_max_usd"] >= body["realistic_max_usd"]
    assert body["optimism_arguments"]
    assert body["digest"]["text"].startswith("OWNEX MAX DAILY INCOME")


def test_max_daily_income_endpoint_empty_uses_workbank(auth_client) -> None:
    resp = auth_client.post("/direct-work/max-daily-income", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "digest" in body
