"""Tests for the execution → revenue bridge + calibration + repeatable signals.

P2: automated execution must feed the RevenueTracker honestly —
SUBMITTED/CONFIRMED never become PAID here (Rule §39, same as income_chain_e2e).
"""

from __future__ import annotations

import pytest

from cores.direct_work_engine.evolution import identify_repeatable, prediction_error_report
from cores.direct_work_engine.feedback import LearningRecord
from cores.opportunity.executors.auto_submit import SubmissionStatus
from cores.revenue_tracker.execution_bridge import (
    WORK_PLATFORM_TO_PAYMENT,
    record_pipeline_outcome,
    record_submission_outcome,
    resolve_payment_platform,
)
from cores.revenue_tracker.revenue_tracker import PaymentStatus, get_revenue_tracker


class _FakeRecord:
    def __init__(self, rid="sub-1", platform="opire", status=SubmissionStatus.SUBMITTED):
        self.id = rid
        self.platform = platform
        self.opportunity_id = "wb-1"
        self.opportunity_title = "Fix login bug"
        self.status = status
        self.attempts = 1
        self.last_error = ""
        self.metadata = {"opportunity": {"title": "Fix login bug", "reward": 150.0, "url": "https://x.test/1"}}


@pytest.fixture()
def tracker():
    t = get_revenue_tracker()
    saved_opps = dict(t.opportunities)
    saved_metrics = dict(t.metrics)
    t.opportunities.clear()
    t.metrics.clear()
    yield t
    t.opportunities.clear()
    t.opportunities.update(saved_opps)
    t.metrics.clear()
    t.metrics.update(saved_metrics)


def test_map_covers_workana_as_dev_bounty():
    assert WORK_PLATFORM_TO_PAYMENT["workana"] == "dev_bounty"
    assert resolve_payment_platform("workana").value == "dev_bounty"
    assert resolve_payment_platform("unknown-xyz").value == "dev_bounty"


def test_submitted_becomes_reviewing_never_paid(tracker):
    opp_id = record_submission_outcome(_FakeRecord(status=SubmissionStatus.SUBMITTED))
    opp = tracker.opportunities[opp_id]
    assert opp.status == PaymentStatus.REVIEWING
    assert opp.revenue_state == "committed"


def test_confirmed_becomes_accepted_never_paid(tracker):
    opp_id = record_submission_outcome(_FakeRecord(status=SubmissionStatus.CONFIRMED))
    opp = tracker.opportunities[opp_id]
    assert opp.status == PaymentStatus.ACCEPTED
    assert opp.revenue_state == "earned"


def test_failed_and_dlq_become_failed(tracker):
    for status in (SubmissionStatus.FAILED, SubmissionStatus.DLQ):
        opp_id = record_submission_outcome(_FakeRecord(rid=f"r-{status.value}", status=status))
        assert tracker.opportunities[opp_id].status == PaymentStatus.FAILED


def test_transient_status_only_creates_pending(tracker):
    opp_id = record_submission_outcome(_FakeRecord(status=SubmissionStatus.SUBMITTING))
    assert tracker.opportunities[opp_id].status == PaymentStatus.PENDING


def test_bridge_is_idempotent(tracker):
    rec = _FakeRecord(status=SubmissionStatus.CONFIRMED)
    first = record_submission_outcome(rec)
    second = record_submission_outcome(rec)
    assert first == second
    assert len(tracker.opportunities) == 1


def test_pipeline_submitted_maps_to_reviewing(tracker):
    opp_id = record_pipeline_outcome("opire", "b-1", "submitted", reward=200.0, url="https://x.test/i/1")
    assert tracker.opportunities[opp_id].status == PaymentStatus.REVIEWING


def test_pipeline_failure_verdicts_map_to_failed(tracker):
    for verdict in ("rejected", "failed", "error"):
        opp_id = record_pipeline_outcome("opire", f"b-{verdict}", verdict)
        assert tracker.opportunities[opp_id].status == PaymentStatus.FAILED


def test_pipeline_unknown_verdict_returns_none(tracker):
    assert record_pipeline_outcome("opire", "b-x", "in_progress") is None
    assert not tracker.opportunities


def test_calibration_unknown_without_predictions():
    report = prediction_error_report([LearningRecord(platform="opire", accepted=True, amount=100.0)])
    assert report["verdict"] == "UNKNOWN"
    assert report["mae_amount_usd"] is None


def test_calibration_computes_errors():
    records = [
        LearningRecord(
            platform="opire",
            accepted=True,
            amount=120.0,
            predicted_amount=100.0,
            predicted_hours=5.0,
            actual_hours=6.0,
            predicted_probability=0.8,
        ),
        LearningRecord(
            platform="opire",
            accepted=False,
            amount=0.0,
            predicted_amount=50.0,
            predicted_hours=2.0,
            actual_hours=2.0,
            predicted_probability=0.4,
        ),
    ]
    report = prediction_error_report(records)
    assert report["mae_amount_usd"] == 35.0
    assert report["mae_hours"] == 0.5
    assert report["mean_probability_error"] == 0.3


def test_identify_repeatable_verdicts():
    records = [
        LearningRecord(platform="opire", accepted=True, amount=100.0),
        LearningRecord(platform="opire", accepted=True, amount=150.0),
        LearningRecord(platform="opire", accepted=False, amount=0.0),
        LearningRecord(platform="hackerone", accepted=True, amount=500.0),
        LearningRecord(platform="fiverr", accepted=False, amount=0.0),
        LearningRecord(platform="fiverr", accepted=False, amount=0.0),
        LearningRecord(platform="fiverr", accepted=False, amount=0.0),
    ]
    rows = {f"{r['platform']}": r for r in identify_repeatable(records)}
    assert rows["opire"]["verdict"] == "REPEATABLE"
    assert rows["hackerone"]["verdict"] == "UNKNOWN"
    assert rows["fiverr"]["verdict"] == "NON_REPEATABLE"


class _FakeEngine:
    def __init__(self, records):
        self._records = records

    def list_submissions(self):
        return list(self._records)


class _FakeItem:
    def __init__(self, iid="wb-9", status="delivered"):
        self.id = iid
        self.status = status
        self.title = "Delivered bounty"
        self.platform = "opire"
        self.reward = 200.0
        self.url = "https://x.test/9"


class _FakeBank:
    def __init__(self, items):
        self._items = {i.id: i for i in items}


def test_reconcile_replays_terminal_submissions(monkeypatch, tracker):
    import cores.direct_work_engine.workbank as wb_mod
    import cores.opportunity.executors.auto_submit as as_mod
    from cores.revenue_tracker.execution_bridge import reconcile_from_persisted_state

    rec = _FakeRecord(rid="sub-r1", platform="opire", status=SubmissionStatus.CONFIRMED)
    monkeypatch.setattr(as_mod, "get_auto_submit_engine", lambda: _FakeEngine([rec]))
    monkeypatch.setattr(wb_mod, "get_workbank", lambda *a, **k: _FakeBank([]))
    counts = reconcile_from_persisted_state()
    assert counts == {"submissions": 1, "delivered": 0, "skipped": 0}
    assert tracker.opportunities["sub_sub-r1"].status == PaymentStatus.ACCEPTED


def test_reconcile_replays_delivered_workbank_items(monkeypatch, tracker):
    import cores.direct_work_engine.workbank as wb_mod
    import cores.opportunity.executors.auto_submit as as_mod
    from cores.revenue_tracker.execution_bridge import reconcile_from_persisted_state

    monkeypatch.setattr(as_mod, "get_auto_submit_engine", lambda: _FakeEngine([]))
    monkeypatch.setattr(wb_mod, "get_workbank", lambda *a, **k: _FakeBank([_FakeItem()]))
    counts = reconcile_from_persisted_state()
    assert counts == {"submissions": 0, "delivered": 1, "skipped": 0}
    # Rule §39: reconcile replays delivery as REVIEWING (submitted, awaiting
    # platform review) — never ACCEPTED/PAID without payout evidence.
    assert tracker.opportunities["wb_wb-9"].status == PaymentStatus.REVIEWING


def test_reconcile_skips_transient_statuses(monkeypatch, tracker):
    import cores.direct_work_engine.workbank as wb_mod
    import cores.opportunity.executors.auto_submit as as_mod
    from cores.revenue_tracker.execution_bridge import reconcile_from_persisted_state

    rec = _FakeRecord(rid="sub-pending", status=SubmissionStatus.SUBMITTING)
    monkeypatch.setattr(as_mod, "get_auto_submit_engine", lambda: _FakeEngine([rec]))
    monkeypatch.setattr(wb_mod, "get_workbank", lambda *a, **k: _FakeBank([_FakeItem(status="ready_to_deliver")]))
    counts = reconcile_from_persisted_state()
    assert counts == {"submissions": 0, "delivered": 0, "skipped": 0}
    assert not tracker.opportunities


class TestQueueSubmissionSync:
    """ExecutionQueue driver SUBMITTED/FAILED transitions must reach the
    RevenueTracker as REVIEWING/FAILED via the bridge SSOT (Rule §39)."""

    def _sync(self):
        from cores.financial.execution_sync import ExecutionRevenueSync

        sync = ExecutionRevenueSync.__new__(ExecutionRevenueSync)
        sync.tracker = get_revenue_tracker()
        return sync

    def test_queue_submitted_becomes_reviewing(self, tracker):
        from cores.execution_queue import ExecState

        sync = self._sync()
        sync._on_state_changed(
            item_id="q-1",
            new_state=ExecState.SUBMITTED.value,
            payload={"platform": "opire", "id": "b-10", "title": "Fix bug", "reward": 200.0},
        )
        opp = tracker.opportunities.get("sub_exec_q-1")
        assert opp is not None
        assert opp.status == PaymentStatus.REVIEWING
        assert opp.revenue_state == "committed"

    def test_queue_failed_becomes_failed(self, tracker):
        from cores.execution_queue import ExecState

        sync = self._sync()
        sync._on_state_changed(
            item_id="q-2",
            new_state=ExecState.FAILED.value,
            payload={"platform": "hackerone", "id": "f-3", "title": "XSS", "reward": 500.0},
        )
        opp = tracker.opportunities.get("sub_exec_q-2")
        assert opp is not None
        assert opp.status == PaymentStatus.FAILED

    def test_other_states_ignored(self, tracker):
        from cores.execution_queue import ExecState

        sync = self._sync()
        sync._on_state_changed(item_id="q-3", new_state=ExecState.EXECUTING.value, payload={})
        assert "sub_exec_q-3" not in tracker.opportunities
