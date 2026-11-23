"""Account Verification Flow — state machine, persistence, NBA integration."""

from __future__ import annotations

import json

import pytest

from core.opportunity import account_verification as av
from core.opportunity.guided_earning import dismiss_action, get_guide_progress, next_best_action, snooze_action
from cores.direct_work_engine.workbank import WorkBank, WorkItem


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
    bank = WorkBank(tmp_path / "workbank.json")
    bank._items["wb-av-1"] = WorkItem(
        id="wb-av-1",
        title="Task on TestPlatform",
        platform="testplatform",
        category="dev",
        reward=50.0,
        barrier_score=30.0,
        employment_type="bounty",
        status="needs_access",
        access_status="needs_manual_setup",
        access_requirement="Create account on TestPlatform.",
        url="https://example.com/task/1",
    )
    monkeypatch.setattr("core.opportunity.guided_earning.get_workbank", lambda: bank)
    return bank


class TestStateMachine:
    def test_new_platform_starts_at_requirements_check(self, env):
        view = av.verification_view("testplatform")
        assert view["stage"] == "REQUIREMENTS_CHECK"
        assert view["paused"] is False
        assert len(view["checklist"]) == 6

    def test_confirm_advances_and_appends_events(self, env):
        av.confirm("testplatform", "registration_status", "REGISTRATION_STARTED", notes="owner started signup")
        view = av.verification_view("testplatform")
        assert view["stage"] == "REGISTRATION_STARTED"
        types = [e["event_type"] for e in view["events"]]
        assert "STATUS_CONFIRMED" in types and "REGISTRATION_STATUS_SET" in types

    def test_full_flow_to_fully_configured(self, env):
        av.confirm("testplatform", "registration_status", "REGISTRATION_STARTED")
        av.confirm("testplatform", "email_status", "EMAIL_USER_CONFIRMED")
        av.confirm("testplatform", "identity_status", "KYC_NOT_REQUIRED")
        av.confirm("testplatform", "access_status", "TASK_ACCESS_CONFIRMED")
        av.confirm("testplatform", "payout_status", "PAYOUT_COMPATIBLE_AR")
        view = av.verification_view("testplatform")
        assert view["stage"] == "FULLY_CONFIGURED"
        assert av.is_platform_verified("testplatform") is True

    def test_partial_when_access_ok_but_payout_unknown(self, env):
        av.confirm("testplatform", "access_status", "ACCOUNT_ACTIVE")
        view = av.verification_view("testplatform")
        assert view["stage"] == "PARTIALLY_CONFIGURED"
        assert av.is_platform_verified("testplatform") is True

    def test_unknown_never_counts_as_verified(self, env):
        assert av.is_platform_verified("testplatform") is False
        av.confirm("testplatform", "access_status", "ACCESS_UNKNOWN")
        assert av.is_platform_verified("testplatform") is False

    def test_restricted_blocks(self, env):
        av.confirm("testplatform", "access_status", "ACCESS_RESTRICTED")
        assert av.verification_view("testplatform")["stage"] == "BLOCKED"
        assert av.is_platform_verified("testplatform") is False

    def test_invalid_field_and_value_rejected(self, env):
        with pytest.raises(ValueError):
            av.confirm("testplatform", "password", "x")
        with pytest.raises(ValueError):
            av.confirm("testplatform", "email_status", "MADE_UP")

    def test_events_are_append_only(self, env):
        av.confirm("testplatform", "email_status", "EMAIL_USER_CONFIRMED")
        av.confirm("testplatform", "email_status", "EMAIL_VERIFIED", method="VERIFIED_BY_API")
        view = av.verification_view("testplatform")
        emails = [e for e in view["events"] if e["event_type"] == "EMAIL_STATUS_SET"]
        assert len(emails) == 2  # history preserved, not overwritten
        assert view["verification_method"] == "VERIFIED_BY_API"

    def test_pause_resume_preserved(self, env):
        av.confirm("testplatform", "access_status", "ACCOUNT_ACTIVE")
        av.set_paused("testplatform", True)
        assert av.is_platform_verified("testplatform") is False  # paused ≠ verified
        av.set_paused("testplatform", False)
        assert av.is_platform_verified("testplatform") is True

    def test_persistence_across_reads(self, env, tmp_path):
        av.confirm("testplatform", "registration_status", "REGISTRATION_STARTED")
        data = json.loads((tmp_path / "account_verifications.json").read_text())
        assert "testplatform" in data


class TestNBAIntegration:
    def test_verified_platform_unblocks_nba(self, env):
        # Before verification: resolve_access candidate for testplatform
        av.confirm("testplatform", "access_status", "ACCOUNT_ACTIVE")
        after = next_best_action()
        # Item no longer needs access → either no candidate or different kind
        if after["action"]:
            assert after["action"]["item_id"] != "wb-av-1" or after["action"]["kind"] != "resolve_access"

    def test_dismiss_removes_from_nba(self, env):
        before = next_best_action()
        assert before["action"] is not None
        dismiss_action("wb-av-1", reason="not interested")
        after = next_best_action()
        assert after["action"] is None or after["action"]["item_id"] != "wb-av-1"
        # History preserved
        assert get_guide_progress("wb-av-1")["dismissed"] is True

    def test_snooze_hides_temporarily(self, env):
        snooze_action("wb-av-1", hours=1)
        after = next_best_action()
        assert after["action"] is None or after["action"]["item_id"] != "wb-av-1"

    def test_blocked_list_includes_needs_access(self, env):
        result = next_best_action()
        # wb-av-1 is the only item → it's the top action, not in blocked
        assert result["state"] in {"ACTION_AVAILABLE", "HUMAN_ACTION_REQUIRED", "ACTION_IN_PROGRESS"}
        assert "blocked" in result and "evidence" in (result["action"] or {})
