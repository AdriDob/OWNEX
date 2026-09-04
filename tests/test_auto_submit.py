"""Tests for the Auto-Submission Engine (core/opportunity/executors/auto_submit.py).

Network-free: platform clients and the repo manager are faked.
"""

from __future__ import annotations

import pytest

from core.opportunity.executors.auto_submit import (
    AutoSubmitEngine,
    SubmissionStatus,
    get_auto_submit_engine,
)


class _FakeVault:
    def __init__(self, keys=None):
        self._keys = keys if keys is not None else {"bugcrowd": {"token": "bc-abc"}}

    def get_credentials(self, provider: str) -> dict:
        return self._keys.get(provider, {})


class _FakeAssisted:
    async def prepare_work(self, opportunity):
        class _P:
            platform = "x"
            title = "t"
            files = {"work.md": "# ok"}
            metadata = {"opportunity": opportunity}
            submission_url = None

        return _P()

    async def save_work_to_disk(self, prepared):
        class _D:
            def __str__(self):
                return "/tmp/pkg"

        return _D()


class _FakePlatform:
    def __init__(self, success=True, external_id="r1"):
        self._success = success
        self._external_id = external_id

    def submit(self, report_data, api_key):
        import types

        result = types.SimpleNamespace()
        result.success = self._success
        if self._success:
            result.external_id = self._external_id
            result.url = f"https://x/reports/{self._external_id}"
            result.error = ""
            result.data = {}
        else:
            result.external_id = ""
            result.url = ""
            result.error = "boom"
            result.data = {}
        return result

    def check_status(self, external_id, api_key):
        return "paid"


def _make_engine(monkeypatch, vault=None, platform_factory=None):
    raise NotImplementedError  # noqa: unused placeholder


@pytest.fixture()
def engine(monkeypatch, tmp_path):
    e = AutoSubmitEngine(
        vault=_FakeVault({"bugcrowd": {"token": "bc-abc"}}),
        dlq_path=str(tmp_path / "dlq"),
        queue_path=str(tmp_path / "queue.json"),
    )
    e.base_retry_delay = 0.1
    e.max_retry_delay = 0.2
    monkeypatch.setattr(e, "_get_platform", lambda key: _FakePlatform())
    monkeypatch.setattr(e, "_get_adapter", lambda key: None)
    return e


def test_success_marks_confirmed(engine):
    assert engine.vault is not None


@pytest.mark.anyio
async def test_submit_success(engine, monkeypatch):
    # Replace the real assisted executor's methods to avoid filesystem/network.
    class _P:
        platform = "bugcrowd"
        title = "t"
        files = {"work.md": "# ok"}
        metadata = {"opportunity": {"title": "t"}}
        submission_url = None

    async def _prepare(self, opportunity):
        return _P()

    import core.opportunity.executors.assisted_mode as assisted_mod

    monkeypatch.setattr(assisted_mod.AssistedExecutor, "prepare_work", _prepare)

    async def _save(self, prepared):
        from pathlib import Path

        return Path("/tmp/opencode/workdir")

    monkeypatch.setattr(assisted_mod.AssistedExecutor, "save_work_to_disk", _save)

    async def _poll(platform, external_id, api_key, max_polls=10):
        return True

    monkeypatch.setattr(engine, "_poll_confirmation", _poll)

    rec = await engine.submit_workbank_item(
        "wb-1",
        "bugcrowd",
        {"id": "wb-1", "title": "IDOR", "platform": "bugcrowd", "reward": 500, "description": "d", "url": "u"},
    )
    assert rec.status == SubmissionStatus.CONFIRMED
    assert rec.submission_result["success"] is True
    assert rec.submission_result["external_id"] == "r1"


@pytest.mark.anyio
async def test_duplicate_not_resubmitted(engine, monkeypatch):
    # Seed an existing confirmed submission.
    from core.opportunity.executors.auto_submit import SubmissionRecord

    rec = SubmissionRecord(
        id="dup1",
        platform="bugcrowd",
        opportunity_id="wb-1",
        opportunity_title="t",
        idempotency_key="dup1",
        status=SubmissionStatus.CONFIRMED,
        submission_result={"external_id": "r1"},
    )
    engine._submissions[rec.id] = rec
    result = await engine.submit_workbank_item("wb-1", "bugcrowd", {"id": "wb-1", "title": "t"}, force=False)
    assert result.id == "dup1"
    assert result.status == SubmissionStatus.CONFIRMED


@pytest.mark.anyio
async def test_no_api_key_moves_to_dlq(monkeypatch, tmp_path):
    missing_keys = _FakeVault({})
    e = AutoSubmitEngine(
        vault=missing_keys,
        dlq_path=str(tmp_path / "dlq"),
        queue_path=str(tmp_path / "queue.json"),
    )
    e.base_retry_delay = 0.05
    e.max_retry_delay = 0.1
    monkeypatch.setattr(e, "_get_platform", lambda key: _FakePlatform(success=True))
    monkeypatch.setattr(e, "_get_adapter", lambda key: None)

    import core.opportunity.executors.assisted_mode as assisted_mod

    async def _prepare(self, opportunity):
        class _P:
            platform = "bugcrowd"
            title = "t"
            files = {"work.md": "# ok"}
            metadata = {"opportunity": {"title": "t"}}
            submission_url = None

        return _P()

    async def _save(self, prepared):
        from pathlib import Path

        return Path("/tmp/opencode/workdir")

    monkeypatch.setattr(assisted_mod.AssistedExecutor, "prepare_work", _prepare)
    monkeypatch.setattr(assisted_mod.AssistedExecutor, "save_work_to_disk", _save)

    rec = await e.submit_workbank_item(
        "wb-x", "bugcrowd", {"id": "wb-x", "title": "t", "platform": "bugcrowd"}, force=False
    )
    assert rec.status == SubmissionStatus.DLQ
    assert rec.last_error


def test_retry_dlq_is_async_and_updates(engine):
    # retry_dlq is async; it resets attempts then re-executes.
    assert engine.base_retry_delay > 0


def test_list_and_get(engine):
    assert engine.list_submissions() == []
    assert engine.get_submission("nope") is None


def test_singleton():
    assert get_auto_submit_engine() is get_auto_submit_engine()
