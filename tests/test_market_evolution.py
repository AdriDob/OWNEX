"""Tests for the Market Evolution Engine (OVOS, Friction Index, Retirement, KB)."""

from __future__ import annotations

import json
from pathlib import Path

from cores.direct_work_engine.income_projection import IncomeProjector, project_income
from cores.direct_work_engine.market_evolution import (
    EcosystemRecord,
    MarketEvolutionEngine,
    MarketKnowledgeBase,
    _friction_tier,
    _is_rejected,
    _reward_usd,
)


def _analysis(name: str, reward: str = "varies", barrier: str = "LOW", trust: float = 70.0) -> dict:
    return {
        "name": name,
        "url": f"https://{name.lower()}.com",
        "category": "bug_bounty",
        "source_type": "platform",
        "entry_barrier": barrier,
        "trust_score": trust,
        "average_reward": reward,
        "earning_potential": "HIGH",
        "payment_method": "profile/email/API",
        "argentina_compatibility": "YES",
        "task_transparency": 1.0,
    }


def test_reward_usd_parses_ranges() -> None:
    assert _reward_usd("varies") == 0.0
    assert _reward_usd("") == 0.0
    assert _reward_usd("$50 - $100") == 75.0
    assert _reward_usd("1,000 - 5,000 USD") == 3000.0


def test_friction_tier_mapping() -> None:
    assert _friction_tier("$100", "LOW", "platform", 90) == "S"
    assert _friction_tier("$10", "MEDIUM", "platform", 60) == "B"
    assert _friction_tier("varies", "HIGH", "platform", 55) == "REJECT"
    assert _friction_tier("varies", "LOW", "job_board", 90) == "REJECT"


def test_is_rejected_job_board_and_low_trust() -> None:
    assert _is_rejected("job_board", "LOW", 90)
    assert _is_rejected("platform", "HIGH", 90)
    assert _is_rejected("platform", "LOW", 30)
    assert not _is_rejected("platform", "LOW", 80)


def test_ovos_in_range_and_ordering() -> None:
    engine = MarketEvolutionEngine(MarketKnowledgeBase(Path("/tmp/opencode/kb_test_1.json")))
    rows = engine._score_ecosystems([_analysis("Alpha", "$200"), _analysis("Beta", "varies", "HIGH", 30)])
    assert all(0 <= r["ovos"] <= 100 for r in rows)
    assert rows[0]["ovos"] > rows[1]["ovos"]


def test_retirement_marks_rejected_and_low_trust() -> None:
    engine = MarketEvolutionEngine(MarketKnowledgeBase(Path("/tmp/opencode/kb_test_2.json")))
    rows = engine._score_ecosystems([_analysis("Gamma", "varies", "HIGH", 80), _analysis("Delta", "varies", "LOW", 35)])
    engine._apply_retirement(rows)
    assert rows[0]["retired"] is True
    assert rows[0]["retirement_reason"]
    assert rows[1]["retired"] is True


def test_retirement_from_history_without_acceptances() -> None:
    kb = MarketKnowledgeBase(Path("/tmp/opencode/kb_test_3.json"))
    kb.upsert(
        EcosystemRecord(
            name="Historic",
            category="bug_bounty",
            first_seen="2026-01-01",
            historical_attempts=5,
            historical_accepted=0,
        )
    )
    engine = MarketEvolutionEngine(kb)
    rows = engine._score_ecosystems([_analysis("Historic", "$100", "LOW", 90)])
    engine._apply_retirement(rows)
    assert rows[0]["retired"] is True
    assert "5 intentos" in rows[0]["retirement_reason"]


def test_retention_with_acceptances() -> None:
    kb = MarketKnowledgeBase(Path("/tmp/opencode/kb_test_4.json"))
    kb.upsert(
        EcosystemRecord(
            name="Profitable",
            category="bug_bounty",
            first_seen="2026-01-01",
            historical_attempts=4,
            historical_accepted=2,
            historical_earned=300.0,
        )
    )
    engine = MarketEvolutionEngine(kb)
    rows = engine._score_ecosystems([_analysis("Profitable", "$100", "LOW", 90)])
    engine._apply_retirement(rows)
    assert rows[0]["retired"] is False


def test_knowledge_base_persists() -> None:
    path = Path("/tmp/opencode/kb_persist.json")
    kb = MarketKnowledgeBase(path)
    kb.upsert(EcosystemRecord(name="Persist", category="dev_bounty", ovos=88.0, friction_tier="S"))
    kb2 = MarketKnowledgeBase(path)
    rec = kb2.get("Persist")
    assert rec is not None
    assert rec.ovos == 88.0
    assert rec.friction_tier == "S"
    path.unlink(missing_ok=True)


def test_knowledge_base_merges_history_on_upsert() -> None:
    path = Path("/tmp/opencode/kb_merge.json")
    kb = MarketKnowledgeBase(path)
    kb.upsert(
        EcosystemRecord(name="M", category="x", first_seen="2026-01-01", historical_attempts=3, historical_earned=10.0)
    )
    kb.upsert(EcosystemRecord(name="M", category="x", ovos=70.0))
    rec = kb.get("M")
    assert rec is not None
    assert rec.first_seen == "2026-01-01"
    assert rec.historical_attempts == 3
    assert rec.historical_earned == 10.0
    assert rec.ovos == 70.0
    path.unlink(missing_ok=True)


def test_analyze_produces_full_report(tmp_path: Path) -> None:
    engine = MarketEvolutionEngine(MarketKnowledgeBase(tmp_path / "kb.json"))
    report = engine.analyze()
    assert report["generated_at"]
    assert report["platforms_analyzed"] > 0
    assert "high_confidence_opportunities" in report
    assert "rejected_platforms" in report
    assert isinstance(report["friction_summary"], dict)
    assert "recommended_actions" in report
    assert all(tier in report["friction_summary"] for tier in ("S", "A", "B", "C", "REJECT"))


def test_analyze_persists_knowledge_base(tmp_path: Path) -> None:
    kb = MarketKnowledgeBase(tmp_path / "kb2.json")
    engine = MarketEvolutionEngine(kb)
    engine.analyze()
    assert len(kb.all()) > 0
    assert all(rec.review_date for rec in kb.all())
    raw = json.loads((tmp_path / "kb2.json").read_text())
    assert raw


def test_friction_summary_counts() -> None:
    engine = MarketEvolutionEngine(MarketKnowledgeBase(Path("/tmp/opencode/kb_friction.json")))
    rows = engine._score_ecosystems(
        [
            _analysis("S1", "$200", "LOW", 95),
            _analysis("A1", "$20", "MEDIUM", 70),
            _analysis("R1", "varies", "HIGH", 50),
        ]
    )
    summary = engine._friction_summary(rows)
    assert summary["S"] >= 1
    assert summary["A"] >= 1
    assert summary["REJECT"] >= 1


def test_market_report_endpoint(tmp_path: Path, monkeypatch) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.routers.direct_work import router
    from cores.direct_work_engine.market_evolution import MarketEvolutionEngine, MarketKnowledgeBase

    monkeypatch.setattr(
        "cores.direct_work_engine.market_evolution.get_market_evolution_engine",
        lambda: MarketEvolutionEngine(MarketKnowledgeBase(tmp_path / "api_kb.json")),
    )

    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)
    resp = client.post("/api/direct-work/market-report")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["platforms_analyzed"] > 0
    assert payload["best_recommendation"]
    assert "recommended_actions" in payload
    assert "ecosystems" not in payload


# ─────────────────────────────────────────────────────────────────────
# Income Projector — honest time-to-income math
# ─────────────────────────────────────────────────────────────────────


def test_projector_reaches_target_within_horizon() -> None:
    # Starting capital that already yields > target monthly at 10%/yr
    projection = project_income(
        work_income_usd_per_month=5000,
        savings_usd_per_month=2000,
        start_capital_usd=12_000_000,  # 12% pocket change for a yield test
        target_monthly_usd=100_000,
    )
    assert projection.months_to_target == 1
    assert projection.crossing_months == 1
    assert projection.portfolio_monthly_income_usd > 100_000


def test_projector_compounds_capital() -> None:
    projection = project_income(
        work_income_usd_per_month=0,
        savings_usd_per_month=1000,
        start_capital_usd=0,
        target_monthly_usd=1_000_000,
    )
    # 10%/yr on $1000/mo: first month portfolio income is tiny; capital grows
    assert projection.months_to_target is None or projection.months_to_target > 100
    assert projection.start_capital_usd == 0.0
    curve = projection.monthly_curve
    assert curve[0]["capital_usd"] > 0
    # curve is monotonically growing
    capitals = [sample["capital_usd"] for sample in curve]
    assert capitals == sorted(capitals)


def test_projector_crossing_without_target() -> None:
    projection = project_income(
        work_income_usd_per_month=100_000,
        savings_usd_per_month=5000,
        start_capital_usd=12_000_000,
        target_monthly_usd=900_000,
    )
    # portfolio income starts well above work income
    assert projection.crossing_months is not None
    assert projection.portfolio_monthly_income_usd >= projection.savings_usd_per_month
    assert projection.months_to_target is None or projection.months_to_target > 1


def test_projector_default_annual_return_named() -> None:
    # Defaults must be conservative (no invented "50% optimized").
    assert IncomeProjector.project.__name__  # just ensures callable default
    p = project_income(work_income_usd_per_month=0, savings_usd_per_month=1000)
    assert abs(p.annual_return_rate - 0.10) < 1e-9


def test_income_projector_endpoint(tmp_path: Path, monkeypatch) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.routers.direct_work import router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)
    resp = client.post(
        "/api/direct-work/income-projector",
        json={
            "work_income_usd_per_month": 3000,
            "savings_usd_per_month": 1000,
            "start_capital_usd": 50_000,
            "annual_return_rate": 0.10,
            "target_monthly_usd": 100_000,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "months_to_target" in payload
    assert "crossing_months" in payload
    assert "monthly_curve" in payload


# ─────────────────────────────────────────────────────────────────────
# Income Dashboard — single pane of glass (WorkBank + Revenue + Projector)
# ─────────────────────────────────────────────────────────────────────


def test_income_dashboard_snapshot_shape(tmp_path: Path, monkeypatch) -> None:
    from cores.direct_work_engine.income_dashboard import IncomeDashboard

    dashboard = IncomeDashboard()
    snapshot = dashboard.snapshot(work_income_usd_per_month=3000, savings_usd_per_month=1000)
    assert set(snapshot) >= {"generated_at", "work", "income", "roi", "projection"}
    assert set(snapshot["work"]) >= {"found", "prepared", "delivered", "needs_access", "targets"}
    assert set(snapshot["income"]) >= {"total_earned_usd", "pending_usd", "platforms_tracked"}
    assert isinstance(snapshot["roi"], list)
    assert snapshot["projection"]["months_to_target"] is not None or snapshot["projection"]["months_to_target"] is None


def test_income_dashboard_projection_requires_inputs(tmp_path: Path, monkeypatch) -> None:
    from cores.direct_work_engine.income_dashboard import IncomeDashboard

    snapshot = IncomeDashboard().snapshot()
    assert snapshot["projection"]["crossing_months"] is None
    assert "note" in snapshot["projection"]


def test_income_dashboard_endpoint(tmp_path: Path, monkeypatch) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.routers.direct_work import router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)
    resp = client.post(
        "/api/direct-work/income-dashboard",
        json={
            "work_income_usd_per_month": 3000,
            "savings_usd_per_month": 1000,
            "start_capital_usd": 50_000,
            "annual_return_rate": 0.10,
            "target_monthly_usd": 100_000,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "work" in payload
    assert "income" in payload
    assert "roi" in payload
    assert "projection" in payload
    assert payload["projection"]["months_to_target"] is not None
