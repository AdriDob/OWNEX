"""Guided Earning System — execution guide, next best action, progress store."""

from __future__ import annotations

import json

import pytest

from core.opportunity.guided_earning import (
    Actor,
    Evidence,
    build_execution_guide,
    complete_guide_step,
    get_guide_progress,
    next_best_action,
    start_guide,
)
from cores.direct_work_engine.workbank import WorkBank, WorkItem


def _item(**overrides) -> WorkItem:
    defaults = dict(
        id="wb-test-1",
        title="Fix pagination bug in OSS repo",
        platform="algora",
        category="bug_fix",
        reward=60.0,
        barrier_score=20.0,
        employment_type="bounty",
        status="needs_access",
        access_status="needs_api_key",
        access_requirement="Registrarse en Algora y conectar GitHub.",
        deliverables=["submission_draft"],
        url="https://github.com/example/repo/issues/1",
        payout_method="crypto",
    )
    defaults.update(overrides)
    return WorkItem(**defaults)


@pytest.fixture()
def bank(tmp_path, monkeypatch):
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
    b = WorkBank(tmp_path / "workbank.json")
    b._items["wb-test-1"] = _item()
    b._items["wb-test-2"] = _item(
        id="wb-test-2",
        title="Ready job",
        platform="github",
        status="ready_to_deliver",
        ready_to_deliver=True,
        access_status="public",
        access_requirement="",
        reward=100.0,
        url="https://github.com/example/repo2/issues/2",
    )
    monkeypatch.setattr("core.opportunity.guided_earning.get_workbank", lambda: b)
    monkeypatch.setattr("api.routers.guided_earning.get_workbank", lambda: b)
    return b


class TestExecutionGuide:
    def test_guide_has_all_sections(self, bank):
        guide = build_execution_guide(bank.get_item("wb-test-1"))
        for section in ("overview", "why", "where_to_go", "requirements", "steps", "technical_plan", "submission_guide", "payment_guide", "progress"):
            assert section in guide

    def test_steps_ordered_and_tagged(self, bank):
        guide = build_execution_guide(bank.get_item("wb-test-1"))
        ids = [s["id"] for s in guide["steps"]]
        assert ids[0] == "verify-availability"
        assert "platform-access" in ids
        assert ids[-1] == "verify-payment"
        for step in guide["steps"]:
            assert step["actor"] in {str(a) for a in Actor}
            assert step["evidence"] in {str(e) for e in Evidence}

    def test_blocked_steps_when_access_missing(self, bank):
        guide = build_execution_guide(bank.get_item("wb-test-1"))
        by_id = {s["id"]: s for s in guide["steps"]}
        assert by_id["submit-work"]["status"] == "blocked"
        assert by_id["platform-access"]["actor"] == str(Actor.HUMAN_REQUIRED)

    def test_public_access_unblocks_flow(self, bank):
        guide = build_execution_guide(bank.get_item("wb-test-2"))
        by_id = {s["id"]: s for s in guide["steps"]}
        assert by_id["submit-work"]["status"] == "pending"
        assert by_id["platform-access"]["status"] == "completed"

    def test_urls_only_from_real_sources(self, bank):
        guide = build_execution_guide(bank.get_item("wb-test-1"))
        where = guide["where_to_go"]
        # algora has a curated platform guide → real URL
        assert where["platform_url"].startswith("https://")
        assert "signup" not in where["platform_url"] or where["platform_url"].endswith("algora.io")
        assert guide["overview"]["reward"] == 60.0
        # No invented register/docs/payment URLs
        assert where["register_url"] == ""
        assert where["docs_url"] == ""
        assert where["payment_url"] == ""

    def test_payment_guide_never_claims_verified(self, bank):
        guide = build_execution_guide(bank.get_item("wb-test-1"))
        assert guide["payment_guide"]["payment_verified"] is False
        assert "no implica" in guide["payment_guide"]["reward_caveat"] or "anunciada" in guide["payment_guide"]["reward_caveat"]

    def test_unknown_platform_still_produces_guide(self, bank):
        item = _item(id="wb-x", platform="plataforma-inexistente-xyz", access_status="public", access_requirement="")
        guide = build_execution_guide(item)
        assert guide["steps"]
        assert guide["where_to_go"]["platform_url"] == ""


class TestProgressStore:
    def test_start_and_complete_persist(self, bank, tmp_path):
        start_guide("wb-test-1")
        complete_guide_step("wb-test-1", "verify-availability")
        complete_guide_step("wb-test-1", "verify-availability")  # idempotent
        progress = get_guide_progress("wb-test-1")
        assert progress["completed_steps"] == ["verify-availability"]
        assert progress["started_at"]
        # File actually persisted
        data = json.loads((tmp_path / "guided_earning.json").read_text())
        assert "wb-test-1" in data

    def test_complete_rejects_unknown_step(self, bank):
        with pytest.raises(ValueError):
            complete_guide_step("wb-test-1", "not-a-step")

    def test_completed_steps_reflected_in_guide(self, bank):
        start_guide("wb-test-1")
        complete_guide_step("wb-test-1", "platform-access")
        guide = build_execution_guide(bank.get_item("wb-test-1"), get_guide_progress("wb-test-1"))
        by_id = {s["id"]: s for s in guide["steps"]}
        assert by_id["platform-access"]["status"] == "completed"
        assert by_id["submit-work"]["status"] == "pending"  # unblocked by access step

    def test_resume_after_reload(self, bank, tmp_path):
        start_guide("wb-test-1")
        complete_guide_step("wb-test-1", "verify-availability")
        # Simulate app restart: progress survives because it lives on disk
        progress = get_guide_progress("wb-test-1")
        assert "verify-availability" in progress["completed_steps"]


class TestNextBestAction:
    def test_prefers_actionable_work(self, bank):
        result = next_best_action()
        assert result["action"] is not None
        # wb-test-2 is ready_to_deliver with reward 100 → highest score
        assert result["action"]["item_id"] == "wb-test-2"
        assert result["action"]["actor"] in {str(a) for a in Actor}
        assert result["alternatives"]

    def test_empty_bank_returns_reason(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        empty = WorkBank(tmp_path / "wb.json")
        monkeypatch.setattr("core.opportunity.guided_earning.get_workbank", lambda: empty)
        result = next_best_action()
        assert result["action"] is None
        assert "discovery" in result["reason"].lower() or "Work Bank" in result["reason"]


class TestWorkspace:
    def test_workspace_aggregates_guide_verification_journey(self, bank):
        from core.opportunity.guided_earning import build_workspace

        ws = build_workspace(bank.get_item("wb-test-1"))
        assert ws["item_id"] == "wb-test-1"
        assert ws["guide"]["steps"]
        assert ws["journey"]["stages"]
        assert ws["account_verification"]["platform"] == "algora"
        assert ws["account_verification"]["verification_url"] == "/earning/verify/algora"
        assert ws["resume"]["step_id"] == ws["guide"]["next_step"]

    def test_workspace_flags_unverified_access_as_blocker(self, bank):
        from core.opportunity.guided_earning import build_workspace

        ws = build_workspace(bank.get_item("wb-test-1"))
        kinds = {b["kind"] for b in ws["blockers"]}
        assert "account_access" in kinds

    def test_workspace_public_item_has_no_access_blocker(self, bank):
        from core.opportunity.guided_earning import build_workspace

        ws = build_workspace(bank.get_item("wb-test-2"))
        assert all(b["kind"] != "account_access" for b in ws["blockers"])
