"""Tests for the Work Bank (autonomous production of zero-barrier jobs) and the Extension Evaluator."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.direct_work import router
from cores.direct_work_engine.extension import ExtensionEvaluator
from cores.direct_work_engine.models import (
    EmploymentType,
    ExperienceLevel,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    WorkPlatform,
)
from cores.direct_work_engine.workbank import WorkBank

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def make_opp(**overrides) -> Opportunity:
    data = {
        "id": "op-1",
        "title": "Fix a public OSS issue",
        "platform": WorkPlatform.OPIRE,
        "category": OpportunityCategory.DEV_BOUNTY,
        "payment": 500.0,
        "payment_method": PaymentMethod.PAYPAL,
        "employment_type": EmploymentType.BOUNTY,
    }
    data.update(overrides)
    return Opportunity(**data)


class TestWorkBank:
    def test_daily_cycle_prepares_ready_items(self, tmp_path) -> None:
        bank = WorkBank(tmp_path / "workbank.json")
        summary = bank.daily_cycle([make_opp()], target=10)
        assert summary["new_items_added"] == 1
        assert summary["ready_to_deliver"] == 1
        item = bank.get_item("op-1")
        assert item is not None
        assert item.ready_to_deliver is True
        assert item.status == "ready_to_deliver"
        assert item.access_status == "public"
        assert item.deliverables

    def test_needs_access_is_flagged_for_manual_platforms(self, tmp_path) -> None:
        bank = WorkBank(tmp_path / "workbank.json")
        bank.daily_cycle([make_opp(id="op-f", platform=WorkPlatform.FREELANCER)], target=10)
        item = bank.get_item("op-f")
        assert item is not None
        assert item.status == "needs_access"
        assert item.ready_to_deliver is False
        assert "perfil" in item.access_requirement.lower()
        assert bank.needs_access()

    def test_zero_barrier_filter_excludes_gated(self, tmp_path) -> None:
        bank = WorkBank(tmp_path / "workbank.json")
        gated = make_opp(
            id="op-hard",
            payment=5000.0,
            experience_required=ExperienceLevel.SENIOR,
            portfolio_required=True,
            interview_required=True,
            technical_test_required=True,
            registration_required=True,
            remote=False,
            payment_method=PaymentMethod.GIFT_CARD,
            time_to_payout_days=90,
            employment_type=EmploymentType.FULL_TIME,
        )
        summary = bank.daily_cycle([gated], target=10)
        assert summary["eligible_zero_barrier"] == 0
        assert bank.get_item("op-hard") is None

    def test_best_ready_orders_by_reward(self, tmp_path) -> None:
        bank = WorkBank(tmp_path / "workbank.json")
        bank.daily_cycle([make_opp(id="op-a", payment=100.0), make_opp(id="op-b", payment=900.0)], target=10)
        best = bank.best_ready(limit=10)
        assert best[0].id == "op-b"
        assert best[0].reward == 900.0

    def test_persistence_survives_restart(self, tmp_path) -> None:
        path = tmp_path / "workbank.json"
        WorkBank(path).daily_cycle([make_opp()], target=10)
        reloaded = WorkBank(path)
        item = reloaded.get_item("op-1")
        assert item is not None
        assert item.ready_to_deliver is True

    def test_mark_delivered(self, tmp_path) -> None:
        bank = WorkBank(tmp_path / "workbank.json")
        bank.daily_cycle([make_opp()], target=10)
        assert bank.mark_delivered("op-1") is True
        item = bank.get_item("op-1")
        assert item is not None
        assert item.status == "delivered"
        assert item.ready_to_deliver is False

    def test_daily_cycle_defaults_to_daily_goal(self, tmp_path) -> None:
        from cores.direct_work_engine.workbank import TARGETS

        assert TARGETS == {"daily": 10, "weekly": 100, "monthly": 1000}
        bank = WorkBank(tmp_path / "workbank.json")
        summary = bank.daily_cycle([make_opp()])
        assert summary["new_items_added"] == 1

    def test_weekly_and_monthly_ranking(self, tmp_path) -> None:
        bank = WorkBank(tmp_path / "workbank.json")
        bank.daily_cycle([make_opp(id=f"op-{i}", payment=float(i + 4)) for i in range(1, 16)], target=20)
        weekly = bank.best_weekly()
        monthly = bank.best_monthly()
        assert len(weekly) == 15
        assert weekly[0].id == "op-15"
        assert len(monthly) == 15
        assert monthly[0].reward == 19.0

    def test_progress_tracks_targets(self, tmp_path) -> None:
        bank = WorkBank(tmp_path / "workbank.json")
        bank.daily_cycle([make_opp()], target=10)
        progress = bank.progress()
        assert progress["daily"]["target"] == 10
        assert progress["daily"]["achieved"] == 1
        assert progress["monthly"]["pct"] == 0.1

    def test_run_daily_cycle_scheduler_entry(self, tmp_path) -> None:
        from cores.direct_work_engine import workbank as wb_module

        wb_module._workbank = WorkBank(tmp_path / "wb_sched.json")
        summary = wb_module.run_daily_cycle(target=5, opportunities=[make_opp()])
        assert summary["new_items_added"] == 1
        assert summary["ready_to_deliver"] == 1


class TestSchedulerJob:
    def test_direct_work_job_registered(self) -> None:
        from core.scheduler.jobs import get_all_jobs

        jobs = get_all_jobs()
        assert "direct_work" in jobs
        ids = [j.job_id for j in jobs["direct_work"]]
        assert "work_bank_daily_cycle" in ids
        handler = [j.handler for j in jobs["direct_work"] if j.job_id == "work_bank_daily_cycle"][0]
        assert handler == "cores.direct_work_engine.workbank:run_daily_cycle"


class TestExtensionEvaluator:
    def test_aligned_proposal_is_approved(self) -> None:
        proposal = ExtensionEvaluator().evaluate(
            "Adapters PayPal",
            "Conectar la plataforma PayPal para cobrar pagos y sincronizar ingresos automáticamente",
        )
        assert proposal.recommendation == "approve"
        assert proposal.value_score >= 0.45

    def test_duplicate_capability_is_declined(self) -> None:
        proposal = ExtensionEvaluator().evaluate("Discover engine", "Otro motor para descubrir oportunidades")
        assert proposal.recommendation == "decline"
        assert proposal.duplicates_existing is True

    def test_reasoning_is_human_readable(self) -> None:
        proposal = ExtensionEvaluator().evaluate("Algo", "descripción")
        assert proposal.reasoning
        assert "aprobación" in proposal.reasoning[-1]


class TestWorkBankApi:
    def test_cycle_and_state_endpoints(self, tmp_path) -> None:
        from unittest.mock import patch

        from cores.direct_work_engine.workbank import WorkBank

        with patch("api.routers.direct_work.get_workbank", return_value=WorkBank(tmp_path / "wb_api.json")):
            cycle = client.post(
                "/direct-work/workbank/cycle",
                json={
                    "opportunities": [_opp_dict(make_opp())],
                    "target": 10,
                },
            )
            assert cycle.status_code == 200
            body = cycle.json()
            assert body["new_items_added"] == 1
            state = client.get("/direct-work/workbank")
            assert state.status_code == 200
            assert state.json()["ready_to_deliver"] == 1
            assert "targets" in state.json()
            assert state.json()["targets"]["daily"]["target"] == 10
            assert state.json()["targets"]["weekly"]["target"] == 100
            assert state.json()["targets"]["monthly"]["target"] == 1000

    def test_extensions_evaluate_endpoint(self) -> None:
        response = client.post(
            "/direct-work/extensions/evaluate",
            json={"name": "Conector Stripe", "description": "Cobrar pagos internacionales y sincronizar ingresos"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "recommendation" in body
        assert body["reasoning"]


def _opp_dict(opp: Opportunity) -> dict:
    from dataclasses import asdict

    return asdict(opp)
