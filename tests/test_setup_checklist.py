"""Tests para el Setup Checklist (configuración progresiva como tarea diaria)."""

from __future__ import annotations

import pytest

import core.setup.checklist as cl
from core.setup.checklist import SetupChecklist, get_setup_checklist


@pytest.fixture()
def all_detectors_false(monkeypatch):
    for name in list(cl._DETECTORS):
        monkeypatch.setitem(cl._DETECTORS, name, lambda: False)


@pytest.fixture()
def checklist(tmp_path, monkeypatch, all_detectors_false):
    return SetupChecklist(store_path=tmp_path / "setup_checklist.json")


class TestCatalog:
    def test_catalog_has_ten_items_with_required_keys(self) -> None:
        required = {"id", "phase", "priority", "title", "why", "est_minutes", "how_to", "auto"}
        items = cl._catalog()
        assert len(items) == 10
        for item in items:
            assert required <= set(item), item["id"]

    def test_phases_covered_and_priorities_unique_per_phase(self) -> None:
        items = cl._catalog()
        phases = {i["phase"] for i in items}
        assert phases == {cl.PHASE_ESSENTIALS, cl.PHASE_PLATFORMS, cl.PHASE_OPTIONAL}
        by_phase: dict[str, list[int]] = {}
        for item in items:
            by_phase.setdefault(item["phase"], []).append(item["priority"])
        for priorities in by_phase.values():
            assert len(priorities) == len(set(priorities))


class TestStatus:
    def test_fresh_status_all_pending_zero_pct(self, checklist: SetupChecklist) -> None:
        status = checklist.status()
        assert status["complete_pct"] == 0
        assert status["done_items"] == 0
        assert len(status["pending"]) == 10
        assert status["complete"] is False
        assert status["next_task"] is not None

    def test_auto_detector_true_completes_item_without_store(self, checklist: SetupChecklist, monkeypatch) -> None:
        monkeypatch.setitem(cl._DETECTORS, "profile_kit", lambda: True)
        status = checklist.status()
        assert "profile_kit" in status["done"]
        assert status["done_items"] == 1
        assert status["complete_pct"] == 10
        assert all(p["id"] != "profile_kit" for p in status["pending"])

    def test_status_shape_has_phases_labels(self, checklist: SetupChecklist) -> None:
        status = checklist.status()
        assert {"essentials", "platforms", "optional"} == set(status["phases"])
        for phase in status["phases"].values():
            assert {"label", "total", "done"} <= set(phase)


class TestNextDailyTask:
    def test_essentials_beat_lower_priority_number_in_later_phase(self, checklist: SetupChecklist) -> None:
        task = checklist.next_daily_task()
        assert task is not None
        assert task["id"] == "profile_kit"
        assert task["phase"] == cl.PHASE_ESSENTIALS

    def test_phase_ranking_over_priority_number(self, checklist: SetupChecklist, tmp_path) -> None:
        pending = [i for i in cl._catalog() if i["id"] in ("payment_accounts", "outlier_onboarding")]
        task = checklist.next_daily_task(pending=pending)
        assert task is not None
        assert task["id"] == "payment_accounts"

    def test_tie_break_by_effort_within_same_phase_priority(self, checklist: SetupChecklist) -> None:
        pending = [i for i in cl._catalog() if i["phase"] == cl.PHASE_OPTIONAL]
        task = checklist.next_daily_task(pending=pending)
        assert task is not None
        assert task["id"] == "obsidian_vault"

    def test_complete_checklist_returns_none(self, checklist: SetupChecklist) -> None:
        assert checklist.next_daily_task(pending=[]) is None


class TestManualItems:
    def test_mark_done_persists_across_instances(self, tmp_path, monkeypatch, all_detectors_false) -> None:
        store = tmp_path / "s.json"
        SetupChecklist(store_path=store).mark_done("outlier_onboarding")
        status = SetupChecklist(store_path=store).status()
        assert "outlier_onboarding" in status["done"]
        assert status["done_items"] == 1

    def test_mark_done_rejects_auto_item(self, checklist: SetupChecklist) -> None:
        with pytest.raises(ValueError):
            checklist.mark_done("profile_kit")

    def test_mark_done_unknown_raises(self, checklist: SetupChecklist) -> None:
        with pytest.raises(KeyError):
            checklist.mark_done("nope")

    def test_mark_undone_removes_manual_done(self, checklist: SetupChecklist) -> None:
        checklist.mark_done("mindrift_onboarding")
        checklist.mark_undone("mindrift_onboarding")
        status = checklist.status()
        assert "mindrift_onboarding" not in status["done"]
        assert any(p["id"] == "mindrift_onboarding" for p in status["pending"])

    def test_corrupt_store_resets_cleanly(self, checklist: SetupChecklist) -> None:
        checklist.mark_done("trading_live")
        checklist.store_path.write_text("{broken json")
        status = checklist.status()
        assert status["done_items"] == 0


class TestComplete:
    def test_complete_when_all_manual_marked_and_detectors_true(
        self, checklist: SetupChecklist, monkeypatch, all_detectors_false
    ) -> None:
        for name in (
            "profile_kit",
            "payment_accounts",
            "bounty_api_key",
            "first_target",
            "obsidian_vault",
            "smtp_mail",
        ):
            monkeypatch.setitem(cl._DETECTORS, name, lambda: True)
        for manual in ("outlier_onboarding", "mindrift_onboarding", "freelance_profile", "trading_live"):
            checklist.mark_done(manual)
        status = checklist.status()
        assert status["complete"] is True
        assert status["complete_pct"] == 100
        assert status["next_task"] is None


class TestSingleton:
    def test_get_setup_checklist_returns_same_instance(self) -> None:
        assert get_setup_checklist() is get_setup_checklist()


class TestApiEndpoints:
    @pytest.fixture()
    def client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routers.setup import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_status_endpoint_returns_contract(self, client) -> None:
        resp = client.get("/api/setup/checklist/status")
        assert resp.status_code == 200
        body = resp.json()
        assert {"complete_pct", "total_items", "done_items", "pending", "phases", "next_task", "complete"} <= set(body)

    def test_mark_done_unknown_returns_404(self, client) -> None:
        assert client.post("/api/setup/checklist/nope/done").status_code == 404

    def test_mark_done_auto_item_returns_400(self, client) -> None:
        assert client.post("/api/setup/checklist/profile_kit/done").status_code == 400

    def test_undone_unknown_returns_404(self, client) -> None:
        assert client.post("/api/setup/checklist/nope/undone").status_code == 404
