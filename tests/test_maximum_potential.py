"""Tests del OWNEX MAXIMUM POTENTIAL ENGINE — Daily Optimization Report."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cores.direct_work_engine.maximum_potential import (
    MaxPotentialEngine,
    _active_capabilities,
    _recent_commits,
)


def _fake_analysis() -> SimpleNamespace:
    return SimpleNamespace(
        total=10,
        accepted=7,
        rejected=3,
        revenue=420.0,
        roi_usd_per_hour=35.0,
        conversion_rate=0.7,
        top_platform_by_revenue="hackerone",
        top_category_by_revenue="bug_bounty",
    )


def test_report_shape() -> None:
    report = MaxPotentialEngine().report()
    for section in (
        "completed_improvements",
        "performance_gains",
        "automation_gains",
        "new_capabilities",
        "problems_discovered",
        "recommended_next_actions",
        "expected_impact",
    ):
        assert section in report
    assert isinstance(report["completed_improvements"], list)
    assert isinstance(report["problems_discovered"], list)


def test_performance_gains_from_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cores.direct_work_engine.evolution as evolution_module
    import cores.direct_work_engine.maximum_potential as mp_module

    monkeypatch.setattr(
        evolution_module,
        "PerformanceAnalyzer",
        lambda: SimpleNamespace(analyze=lambda records: _fake_analysis()),
    )
    monkeypatch.setattr(
        mp_module,
        "_safe",
        lambda fn, default=None: fn() if fn.__name__ == "lambda" else default,
    )
    monkeypatch.setattr(
        mp_module,
        "_safe",
        lambda fn, default=None: fn() if callable(fn) else default,
    )
    gains = mp_module.MaxPotentialEngine._performance_gains()
    assert gains["conversion_rate"] == 0.7
    assert gains["revenue_usd"] == 420.0
    assert gains["roi_usd_per_hour"] == 35.0


def test_performance_gains_empty_is_honest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cores.direct_work_engine.feedback as feedback_module

    monkeypatch.setattr(feedback_module, "build_history_from_revenue_tracker", lambda t: [])
    gains = MaxPotentialEngine._performance_gains()
    assert gains.get("note") or gains.get("total_outcomes", 0) == 0


def test_automation_gains_with_bank(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cores.direct_work_engine import workbank as wb_module

    bank = wb_module.WorkBank(store_path=tmp_path / "bank.json")
    bank._items = {
        "a1": wb_module.WorkItem(
            id="a1",
            title="Automated scraper",
            platform="fiverr",
            category="web_scraping",
            reward=80.0,
            barrier_score=80.0,
            employment_type="contract",
            status="ready_to_deliver",
            ready_to_deliver=True,
        )
    }
    import cores.direct_work_engine.maximum_potential as mp_module

    monkeypatch.setattr(mp_module, "_safe", lambda fn, default=None: fn())
    gains = mp_module.MaxPotentialEngine._automation_gains()
    assert gains["prepared_jobs"] >= 1
    assert 0 <= gains["avg_automation_pct"] <= 100


def test_problems_detects_low_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cores.direct_work_engine.maximum_potential as mp_module

    low = SimpleNamespace(score=0.5, status="degraded")
    monkeypatch.setattr(mp_module, "_health_snapshot", lambda: low)
    monkeypatch.setattr(mp_module, "_broken_capabilities", lambda: [])
    monkeypatch.setattr(mp_module, "_needs_access_jobs", lambda: [])
    problems = mp_module.MaxPotentialEngine._problems_discovered()
    assert any("salud del sistema" in p for p in problems)
    assert any("0.5" in p for p in problems)


def test_problems_empty_when_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cores.direct_work_engine.maximum_potential as mp_module

    monkeypatch.setattr(mp_module, "_health_snapshot", lambda: None)
    monkeypatch.setattr(mp_module, "_broken_capabilities", lambda: [])
    monkeypatch.setattr(mp_module, "_needs_access_jobs", lambda: [])
    assert mp_module.MaxPotentialEngine._problems_discovered() == []


def test_expected_impact_honest_without_income(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cores.direct_work_engine.maximum_potential as mp_module

    monkeypatch.setattr(mp_module, "_monthly_work_income", lambda: 0.0)
    impact = mp_module.MaxPotentialEngine._expected_impact()
    assert impact["monthly_work_income_usd"] == 0.0
    assert "note" in impact["projection"]


def test_expected_impact_with_income(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cores.direct_work_engine.maximum_potential as mp_module

    monkeypatch.setattr(mp_module, "_monthly_work_income", lambda: 500.0)
    impact = mp_module.MaxPotentialEngine._expected_impact()
    assert impact["monthly_work_income_usd"] == 500.0
    assert "months_to_target" in impact["projection"] or "note" in impact["projection"]


def test_digest_matches_spec_format() -> None:
    report = MaxPotentialEngine().report()
    digest = MaxPotentialEngine.digest(report)
    text = digest["text"]
    assert text.startswith("OWNEX EVOLUTION REPORT")
    for line in (
        "Completed improvements:",
        "Performance gains:",
        "Automation gains:",
        "New capabilities:",
        "Problems discovered:",
        "Recommended next actions:",
        "Expected impact:",
    ):
        assert line in text


def test_digest_with_problem_line() -> None:
    report = MaxPotentialEngine().report()
    report["problems_discovered"] = ["salud del sistema degraded (score 0.5)"]
    digest = MaxPotentialEngine.digest(report)
    assert "degraded" in digest["text"]


def test_recent_commits_uses_git() -> None:
    commits = _recent_commits()
    assert isinstance(commits, list)


def test_active_capabilities_from_registry() -> None:
    caps = _active_capabilities()
    assert isinstance(caps, list)


def test_report_is_defensive_when_engines_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cores.direct_work_engine.maximum_potential as mp_module

    def boom() -> None:
        raise RuntimeError("engine down")

    monkeypatch.setattr(mp_module, "_safe", lambda fn, default=None: default)
    report = mp_module.MaxPotentialEngine().report()
    assert report["completed_improvements"] == []
    assert isinstance(report["performance_gains"], dict)
    assert isinstance(report["automation_gains"], dict)
    assert report["new_capabilities"] == []
    assert report["problems_discovered"] == []
    assert isinstance(report["recommended_next_actions"], list)
    assert isinstance(report["expected_impact"], dict)


@pytest.fixture(scope="module")
def auth_client():
    from fastapi.testclient import TestClient

    from api.main import app
    from cores.license.validator import generate_license

    client = TestClient(app)
    lic = generate_license(expiry_days=365)
    client.post("/api/license/activate", json={"key": lic})
    resp = client.post("/api/auth/login", json={"device_id": "pytest-max-potential"})
    if resp.status_code == 200:
        client.headers.update({"Authorization": f"Bearer {resp.json()['data']['token']}"})
    resp = client.get("/api/version")
    csrf_token = resp.cookies.get("csrf-token")
    if csrf_token:
        client.headers.update({"X-CSRF-Token": csrf_token})
    return client


def test_evolution_report_endpoint(auth_client) -> None:
    resp = auth_client.post("/direct-work/evolution-report")
    assert resp.status_code == 200
    body = resp.json()
    assert "completed_improvements" in body
    assert "digest" in body
    assert body["digest"]["text"].startswith("OWNEX EVOLUTION REPORT")
    assert isinstance(body["expected_impact"], dict)


def test_save_daily_report_writes_file(tmp_path) -> None:
    import cores.direct_work_engine.maximum_potential as mp_module

    report = {"generated_at": "2026-08-05T06:45:00+00:00", "automation_gains": {"prepared_jobs": 5}}
    path = mp_module.save_daily_report(report, report_dir=tmp_path)
    assert path is not None
    saved = json.loads(Path(path).read_text())
    assert saved["automation_gains"]["prepared_jobs"] == 5


def test_save_daily_report_fails_silently(tmp_path, monkeypatch) -> None:
    import cores.direct_work_engine.maximum_potential as mp_module

    monkeypatch.setattr(mp_module, "datetime", None)
    assert mp_module.save_daily_report({}, report_dir=tmp_path) is None


def test_report_history_returns_snapshots_sorted(tmp_path) -> None:
    import cores.direct_work_engine.maximum_potential as mp_module

    for day, jobs in (("2026-08-03", 3), ("2026-08-04", 7), ("2026-08-05", 10)):
        report = {
            "generated_at": f"{day}T06:45:00+00:00",
            "automation_gains": {"prepared_jobs": jobs, "avg_automation_pct": 80},
            "performance_gains": {"revenue_usd": 100 * jobs},
            "problems_discovered": [],
            "recommended_next_actions": [],
        }
        path = tmp_path / f"evolution_{day}.json"
        path.write_text(json.dumps(report))
    history = mp_module.report_history(limit=10, report_dir=tmp_path)
    assert [h["date"] for h in history] == ["2026-08-05", "2026-08-04", "2026-08-03"]
    assert history[0]["prepared_jobs"] == 10
    assert history[2]["revenue_usd"] == 300.0


def test_report_history_empty_without_dir(tmp_path) -> None:
    import cores.direct_work_engine.maximum_potential as mp_module

    assert mp_module.report_history(report_dir=tmp_path / "missing") == []


def test_trend_compares_with_previous_day(tmp_path) -> None:
    import cores.direct_work_engine.maximum_potential as mp_module

    previous = {
        "automation_gains": {"prepared_jobs": 10, "avg_automation_pct": 70},
        "performance_gains": {"revenue_usd": 200.0},
        "problems_discovered": ["a", "b"],
    }
    current = {
        "automation_gains": {"prepared_jobs": 15, "avg_automation_pct": 80},
        "performance_gains": {"revenue_usd": 320.0},
        "problems_discovered": ["a"],
    }
    trend = mp_module._compare_reports(previous, current)
    assert trend["prepared_jobs"] == 5
    assert trend["avg_automation_pct"] == 10.0
    assert trend["problems_delta"] == -1
    assert trend["revenue_usd_delta"] == 120.0


def test_trend_note_without_metrics(tmp_path) -> None:
    import cores.direct_work_engine.maximum_potential as mp_module

    trend = mp_module._compare_reports({}, {})
    assert trend["note"] == "sin reporte previo comparable"


def test_get_evolution_report_includes_trend(tmp_path, monkeypatch) -> None:
    import cores.direct_work_engine.maximum_potential as mp

    prev_path = tmp_path / "evolution_2026-08-03.json"
    prev_path.write_text(json.dumps({"automation_gains": {"prepared_jobs": 4}}))
    monkeypatch.setattr(mp, "_latest_report", lambda exclude_today=False: json.loads(prev_path.read_text()))
    report = mp.get_evolution_report()
    assert "trend" in report
    assert report["trend"]["prepared_jobs"] > 0 or report["trend"].get("note")
    assert report["digest"]["text"].startswith("OWNEX EVOLUTION REPORT")


def test_daily_handler_runs_and_persists(tmp_path, monkeypatch) -> None:
    import cores.direct_work_engine.maximum_potential as mp_module
    from core.cycles import tasks

    monkeypatch.setattr(mp_module, "get_evolution_report", lambda: {"digest": {"text": "OK"}, "trend": {}})
    monkeypatch.setattr(mp_module, "save_daily_report", lambda report, report_dir=None: str(tmp_path / "x.json"))
    result = tasks.run_daily_evolution_report()
    assert result["status"] == "ok"
    assert result["report_path"] == str(tmp_path / "x.json")


def test_daily_handler_fails_gracefully(monkeypatch) -> None:
    from core.cycles import tasks

    monkeypatch.setattr(
        "cores.direct_work_engine.maximum_potential.get_evolution_report",
        lambda: (_ for _ in ()).throw(RuntimeError("engine down")),
    )
    result = tasks.run_daily_evolution_report()
    assert result["status"] == "error"
    assert "engine down" in result["message"]


def test_evolution_report_history_endpoint(auth_client) -> None:
    resp = auth_client.get("/direct-work/evolution-report/history")
    assert resp.status_code == 200
    body = resp.json()
    assert "history" in body
    assert isinstance(body["history"], list)
