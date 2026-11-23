"""Tests for TaskmarketExecutor — gated write surface for api.taskmarket.dev.

Proves: read actions run without approval, mutating actions fail closed
without credentials, and the queue driver never reaches the executor for
mutating actions unless payload.approved is set.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from core.opportunity.executors.taskmarket_executor import TaskmarketExecutor


@pytest.fixture
def executor():
    return TaskmarketExecutor({})


@pytest.fixture
def executor_with_creds():
    return TaskmarketExecutor({"identity_token": "tok-test"})


class TestGates:
    def test_mutating_without_credentials_fails_closed(self, executor):
        for action, kwargs in (
            ("submit_pitch", {"task_id": "t1", "pitch_text": "hi"}),
            ("submit_work", {"task_id": "t1", "payload": {}}),
            ("request_upload_url", {"task_id": "t1", "filename": "a.md"}),
        ):
            res = asyncio.run(executor.execute(action, **kwargs))
            assert res.success is False
            assert "B6" in (res.error or "")

    def test_unknown_action_fails(self, executor):
        res = asyncio.run(executor.execute("delete_everything", task_id="t1"))
        assert res.success is False
        assert "Unknown action" in (res.error or "")

    def test_health_check_hits_public_api(self, executor):
        res = asyncio.run(executor.execute("health_check"))
        # Live public endpoint — may fail offline; only assert contract shape.
        assert res.action == "health_check"
        assert isinstance(res.success, bool)


class TestAuthorizedClient:
    def test_submit_pitch_with_creds_calls_api(self, executor_with_creds, monkeypatch):
        fake = MagicMock()
        fake.submit_pitch.return_value = {"id": "pitch-1"}
        monkeypatch.setattr(
            "core.opportunity.executors.taskmarket_executor.TaskmarketActions",
            lambda credentials, authorized: fake,
        )
        res = asyncio.run(executor_with_creds.execute("submit_pitch", task_id="tsk-1", pitch_text="pitch"))
        assert res.success is True
        fake.submit_pitch.assert_called_once_with("tsk-1", "pitch")

    def test_list_pitches_is_read_and_needs_no_creds(self, executor, monkeypatch):
        fake = MagicMock()
        fake.list_pitches.return_value = {"pitches": []}
        monkeypatch.setattr(
            "core.opportunity.executors.taskmarket_executor.TaskmarketActions",
            lambda credentials, authorized: fake,
        )
        res = asyncio.run(executor.execute("list_pitches", task_id="tsk-1"))
        assert res.success is True


class TestDriverGate:
    def test_taskmarket_actions_are_mutating_gated(self):
        from core.execution_queue.driver import _MUTATING_ACTIONS

        for action in ("submit_pitch", "submit_work", "request_upload_url"):
            assert action in _MUTATING_ACTIONS

    def test_driver_blocks_unapproved_mutating_before_executor(self, tmp_path, monkeypatch):
        from core.execution_queue import driver as drv

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        out = drv._run_platform_executor(
            "core.opportunity.executors.taskmarket_executor",
            "TaskmarketExecutor",
            "submit_work",
            {"task_id": "t1", "payload": {}},
        )
        assert out["requires_human"] is True
        assert out["submitted"] is False
        assert out["result"]["gate"] == "human_approval_required"
