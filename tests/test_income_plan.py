"""Tests para el Unified Income Plan (fusión first-day + postulaciones + work bank)."""

from __future__ import annotations

from typing import Any

import pytest

from core.application_assistant import ApplicationAssistant
from cores.direct_work_engine.income_plan import UnifiedIncomePlan
from cores.direct_work_engine.workbank import WorkBank, WorkItem
from cores.result_based import FirstDayGuide


def _ready_item(item_id: str = "wb-1", reward: float = 80.0) -> WorkItem:
    return WorkItem(
        id=item_id,
        title="Fix null check in parser",
        platform="opire",
        category="dev_bounty",
        reward=reward,
        barrier_score=85.0,
        employment_type="bounty",
        status="ready_to_deliver",
        ready_to_deliver=True,
    )


class _StubBank:
    """WorkBank mínimo: solo lo que lee el plan."""

    def __init__(self, items: list[WorkItem] | None = None) -> None:
        self._items = items or []

    def best_ready(self, limit: int = 3) -> list[WorkItem]:
        return [i for i in self._items if i.status == "ready_to_deliver"][:limit]

    def progress(self) -> dict[str, dict]:
        ready = len([i for i in self._items if i.status == "ready_to_deliver"])
        return {"daily": {"achieved": ready, "target": 10}}


@pytest.fixture()
def fresh_assistant(tmp_path):
    return ApplicationAssistant(store_path=tmp_path / "applications.json")


@pytest.fixture()
def fresh_first_day(tmp_path):
    return FirstDayGuide(tmp_path / "first_day.json")


class TestFreshState:
    def test_bootstrap_unlock_wins_when_no_stream_accepted(
        self, fresh_assistant: ApplicationAssistant, fresh_first_day: FirstDayGuide
    ) -> None:
        """Regla bootstrap (2026-08-25): sin streams aprobados, la primera
        plataforma de catálogo con tarifa documentada se desbloquea primero."""
        plan = UnifiedIncomePlan(fresh_assistant, fresh_first_day, _StubBank()).build()
        nxt = plan["next_action"]
        assert nxt is not None
        assert nxt["source"] == "applications"
        assert "Outlier" in nxt["title"]
        assert nxt["unlocks_stream"]["hourly_rate_usd"] == 13.0

    def test_plan_shape(self, fresh_assistant: ApplicationAssistant, fresh_first_day: FirstDayGuide) -> None:
        plan = UnifiedIncomePlan(fresh_assistant, fresh_first_day, _StubBank()).build()
        assert set(plan) >= {
            "next_action",
            "phases",
            "tracks",
            "income_command_center",
            "philosophy",
        }
        cc = plan["income_command_center"]
        assert set(cc) >= {"today", "week", "fortnight", "month", "basis", "active_stack"}
        assert plan["tracks"]["active"]["first_day_progress_pct"] == 0.0
        assert plan["tracks"]["passive"]["progress_pct"] == 0

    def test_phase_now_contains_active_and_passive_heads(
        self, fresh_assistant: ApplicationAssistant, fresh_first_day: FirstDayGuide
    ) -> None:
        now = UnifiedIncomePlan(fresh_assistant, fresh_first_day, _StubBank()).build()["phases"]["now"]
        sources = {item["source"] for item in now}
        assert sources >= {"applications", "first_day"}

    def test_no_network_calls_needed(
        self, fresh_assistant: ApplicationAssistant, fresh_first_day: FirstDayGuide, monkeypatch
    ) -> None:
        def _boom(*a: Any, **k: Any) -> None:
            raise AssertionError("el plan combinado no debe descubrir en red")

        monkeypatch.setattr("cores.direct_work_engine.workbank.WorkBank.daily_cycle", _boom)
        UnifiedIncomePlan(fresh_assistant, fresh_first_day, _StubBank()).build()


class TestDeliverPriority:
    def test_ready_item_beats_bootstrap(
        self, fresh_assistant: ApplicationAssistant, fresh_first_day: FirstDayGuide
    ) -> None:
        """Plata sobre la mesa: la entrega lista gana incluso al bootstrap."""
        bank = _StubBank([_ready_item()])
        plan = UnifiedIncomePlan(fresh_assistant, fresh_first_day, bank).build()
        nxt = plan["next_action"]
        assert nxt["source"] == "workbank"
        assert nxt["payoff_range"]["low"] == 80.0

    def test_today_reflects_bank_reward(
        self, fresh_assistant: ApplicationAssistant, fresh_first_day: FirstDayGuide
    ) -> None:
        bank = _StubBank([_ready_item(reward=120.0)])
        cc = UnifiedIncomePlan(fresh_assistant, fresh_first_day, bank).build()["income_command_center"]
        assert cc["ready_to_deliver_count"] == 1
        assert cc["today"]["low"] >= 120.0

    def test_empty_bank_today_comes_from_documented_fd_payoff(
        self, fresh_assistant: ApplicationAssistant, fresh_first_day: FirstDayGuide
    ) -> None:
        cc = UnifiedIncomePlan(fresh_assistant, fresh_first_day, _StubBank()).build()["income_command_center"]
        assert cc["ready_to_deliver_count"] == 0
        assert "sin streams aprobados" in cc["basis"]["note"]


class TestPassiveTrack:
    def test_completed_outlier_step_keeps_outlier_as_bootstrap(self, tmp_path, fresh_first_day: FirstDayGuide) -> None:
        """Completado el paso 1 de Outlier, la secuencia de Outlier continúa
        siendo el bootstrap (no salta a Mercor)."""
        store = tmp_path / "applications.json"
        assistant = ApplicationAssistant(store_path=store)
        assistant.complete_step("outlier", "create_account")

        plan = UnifiedIncomePlan(assistant, fresh_first_day, _StubBank()).build()
        nxt = plan["next_action"]
        assert nxt["source"] == "applications"
        assert "Outlier" in nxt["title"]

    def test_accepted_platform_leaves_queue_and_reviewed_waits(self, tmp_path, fresh_first_day: FirstDayGuide) -> None:
        store = tmp_path / "applications.json"
        assistant = ApplicationAssistant(store_path=store)
        assistant.set_status("outlier", "accepted")
        assistant.set_status("mercor", "in_review")

        plan = UnifiedIncomePlan(assistant, fresh_first_day, _StubBank()).build()
        actionable = plan["phases"]["now"] + plan["phases"]["this_week"]
        app_keys = {i.get("platform_key") or i.get("platform") for i in actionable if i["source"] == "applications"}
        assert "outlier" not in app_keys
        waiting_keys = {w["key"] for w in plan["phases"]["waiting"]}
        assert waiting_keys == {"mercor"}
        # Con Outlier aceptado hay stream activo: deja de ser bootstrap.
        assert plan["tracks"]["passive"]["accepted_streams"] == ["outlier"]

    def test_active_stack_documents_rates(
        self, fresh_assistant: ApplicationAssistant, fresh_first_day: FirstDayGuide
    ) -> None:
        cc = UnifiedIncomePlan(fresh_assistant, fresh_first_day, _StubBank()).build()["income_command_center"]
        outlier = next(s for s in cc["active_stack"] if s["key"] == "outlier")
        assert outlier["rate_documented"] == 13.0
        assert outlier["status"] == "pending"


class TestActiveTrackProgression:
    def test_all_first_day_done_next_is_applications_when_streams_pending(
        self, tmp_path, fresh_assistant: ApplicationAssistant
    ) -> None:
        fd = FirstDayGuide(tmp_path / "first_day.json")
        for step in range(1, 6):
            fd.save_step_complete(step)

        plan = UnifiedIncomePlan(fresh_assistant, fd, _StubBank()).build()
        assert plan["next_action"]["source"] == "applications"

    def test_all_apps_paused_falls_back_to_fd_sequence(self, fresh_assistant: ApplicationAssistant, tmp_path) -> None:
        fd = FirstDayGuide(tmp_path / "first_day.json")
        fd.save_step_complete(1)
        fd.save_step_complete(2)

        for key in ("outlier", "mercor", "alignerr", "mindrift", "fiverr"):
            fresh_assistant.set_status(key, "paused")

        plan = UnifiedIncomePlan(fresh_assistant, fd, _StubBank()).build()
        nxt = plan["next_action"]
        assert nxt["source"] == "first_day"
        # Ranking por $EV/hora conservador: el paso 4 (setup manual, 0.5 h)
        # supera al paso 3 (bug bounty, 4 h) — 100 vs 12.5 USD/h documentados.
        assert nxt["step_number"] == 4


class TestEndpointContract:
    def test_router_exposes_income_plan(self) -> None:
        from api.routers.control import router

        paths = {getattr(r, "path", "") for r in router.routes}
        assert "/api/applications/income-plan" in paths


class TestRealWorkBankIntegration:
    def test_with_real_workbank_tmp_store(self, tmp_path, fresh_assistant, fresh_first_day) -> None:
        store = tmp_path / "workbank.json"
        bank = WorkBank(store_path=store)
        item = _ready_item()
        bank._items[item.id] = item
        bank._save()

        reloaded = WorkBank(store_path=store)
        plan = UnifiedIncomePlan(fresh_assistant, fresh_first_day, reloaded).build()
        assert plan["next_action"]["source"] == "workbank"
        assert plan["tracks"]["active"]["workbank_ready_to_deliver"] == 1


class TestMultiStreamHourBudget:
    def test_two_accepted_streams_do_not_double_count_hours(
        self, tmp_path, fresh_first_day: FirstDayGuide, monkeypatch
    ) -> None:
        """Con 2 streams aceptados el rango NO puede ser la suma de rate×horas.

        Las horas son una sola bolsa: el ingreso/hora está acotado entre el peor
        y el mejor rate aceptado × disponibilidad (50%–100%).
        """
        store = tmp_path / "applications.json"
        assistant = ApplicationAssistant(store_path=store)
        assistant.set_status("outlier", "accepted")  # $13/h
        assistant.set_status("mercor", "accepted")  # $25/h

        availability = 40.0
        monkeypatch.setattr(
            "cores.direct_work_engine.income_plan.get_available_hours", lambda _w: availability
        )

        plan = UnifiedIncomePlan(assistant, fresh_first_day, _StubBank()).build()
        cc = plan["income_command_center"]

        # Aísla el componente recurrente de streams (today suma acciones puntuales).
        stream_week_high = cc["week"]["high"] - cc["today"]["high"]
        stream_month_high = cc["month"]["high"] - cc["today"]["high"]
        # Suma ingenua sería ($13+$25)×40 = $1,520/semana — prohibido.
        assert stream_week_high <= 25.0 * availability + 0.01
        assert stream_month_high <= 25.0 * availability * 4.33 + 0.01
        # Low usa el peor rate aceptado al 50%.
        stream_week_low = cc["week"]["low"] - cc["today"]["low"]
        assert stream_week_low >= 13.0 * availability * 0.5 - 0.01

    def test_single_stream_matches_documented_rate(
        self, tmp_path, fresh_first_day: FirstDayGuide, monkeypatch
    ) -> None:
        store = tmp_path / "applications.json"
        assistant = ApplicationAssistant(store_path=store)
        assistant.set_status("mercor", "accepted")

        monkeypatch.setattr(
            "cores.direct_work_engine.income_plan.get_available_hours", lambda _w: 40.0
        )

        plan = UnifiedIncomePlan(assistant, fresh_first_day, _StubBank()).build()
        cc = plan["income_command_center"]
        stream_week_high = cc["week"]["high"] - cc["today"]["high"]
        assert stream_week_high == pytest.approx(25.0 * 40.0, abs=0.01)
