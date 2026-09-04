from __future__ import annotations

import asyncio

import pytest

from database.db import SessionLocal
from database.models import WorkerCheckpoint
from cores.worker_core import WorkerCore, WorkGoal, WorkerConfig, AutonomyLevel, WorkPhase, WorkItem
from cores.worker_core.orchestrator import WorkerCore as WC
from cores.worker_core.persistence import (
    checkpoint_data_dict,
    get_active_work_items,
    get_latest_checkpoint,
    resume_from,
    save_checkpoint,
)


class TestCheckpointPersistence:
    """Save/load round-trip for the worker_checkpoints table."""

    def test_save_and_load_roundtrip(self):
        save_checkpoint("work-abc", "discover", {"found": True}, work_item_title="Fix bug", phase_completed=True)
        cp = get_latest_checkpoint("work-abc")
        assert cp is not None
        assert str(cp.work_item_id) == "work-abc"
        assert str(cp.phase) == "discover"
        assert str(cp.phase_completed) == "true"
        data = checkpoint_data_dict(cp)
        assert data is not None
        assert data.get("found") is True

    def test_latest_checkpoint_is_most_recent(self):
        save_checkpoint("work-xyz", "discover", {}, phase_completed=True)
        save_checkpoint("work-xyz", "select", {"picked": True}, phase_completed=True)
        cp = get_latest_checkpoint("work-xyz")
        assert cp is not None
        assert str(cp.phase) == "select"
        data = checkpoint_data_dict(cp)
        assert data is not None
        assert data.get("picked") is True

    def test_active_work_items_lists_work(self):
        save_checkpoint("work-list-1", "evaluate", {}, phase_completed=True)
        active = get_active_work_items()
        assert "work-list-1" in active

    def test_checkpoint_data_missing_returns_none(self):
        assert checkpoint_data_dict(None) is None


class TestResumeLogic:
    """Resume phase determination from persisted checkpoints."""

    def _make(self, phase: str, completed: bool):
        cp = WorkerCheckpoint(work_item_id="w", phase=phase, phase_completed="true" if completed else "false")
        return cp

    def test_completed_discover_returns_evaluate(self):
        assert resume_from(self._make("discover", True)) == "evaluate"

    def test_completed_execute_returns_validate(self):
        assert resume_from(self._make("execute", True)) == "validate"

    def test_interrupted_execute_reruns_execute(self):
        assert resume_from(self._make("execute", False)) == "execute"

    def test_completed_learn_returns_none(self):
        assert resume_from(self._make("learn", True)) is None

    def test_unknown_phase_returns_none(self):
        assert resume_from(self._make("bogus", True)) is None


class TestWorkerCoreResume:
    """WorkerCore resume capability (start rehydrates persisted items)."""

    @pytest.fixture
    def config(self):
        return WorkerConfig(autonomy_level=AutonomyLevel.PREPARE, test_mode=True)

    @pytest.fixture
    def goal(self):
        return WorkGoal(description="Test", target_monthly_usd=1000)

    @pytest.mark.asyncio
    async def test_resume_open_work_items_reports_phase(self, config, goal):
        core = WorkerCore(config)
        core.set_goal(goal)
        # Persist a checkpoint that says execute completed -> should resume at validate.
        save_checkpoint("resume-w1", "execute", {"done": True}, work_item_title="X", phase_completed=True)
        resumed = core.resume_open_work_items()
        assert ("resume-w1", "validate") in resumed
        await core.stop()

    @pytest.mark.asyncio
    async def test_rehydrate_work_item_reconstructs_item(self, config, goal):
        """Test that _rehydrate_work_item reconstructs a WorkItem from checkpoint."""
        from cores.worker_core import WorkerCore, WorkItem

        core = WorkerCore(config)
        core.set_goal(goal)

        # Create a checkpoint with known data
        save_checkpoint(
            "rehydrate-test",
            "prepare",
            {"ready": True, "custom_field": "test_value"},
            work_item_title="Test Item",
            work_item_platform="opire",
            work_item_category="dev_bounty",
            phase_completed=True,
        )

        # Rehydrate directly without starting the core
        core._rehydrate_work_item("rehydrate-test", "execute")

        item = core.work_items.get("rehydrate-test")
        assert item is not None
        assert item.id == "rehydrate-test"
        assert item.phase == WorkPhase.EXECUTE
        assert item.platform == "opire"
        assert item.category == "dev_bounty"
        assert item.estimated_reward_usd == 0.0  # not in checkpoint, defaults to 0
        await core.stop()


class FakeEvaluationEngine:
    """Evaluation engine that returns a quality gate result."""

    def __init__(self, gate_passed: bool):
        self.gate_passed = gate_passed

    def evaluate(self, opportunity):
        return {
            "quality_gate_result": {
                "passed": self.gate_passed,
                "reason": "OK" if self.gate_passed else "No evidence",
            }
        }


class TestMandatoryQualityGate:
    """Quality Gate is mandatory before delivery."""

    def _core_with_gate(self, gate_passed: bool, autonomy_full: bool = True) -> WorkerCore:
        config = WorkerConfig(
            autonomy_level=AutonomyLevel.FULL if autonomy_full else AutonomyLevel.PREPARE,
            human_approval_required=not autonomy_full,
            test_mode=True,
        )
        core = WorkerCore(config)
        core.set_evaluation_engine(FakeEvaluationEngine(gate_passed))
        return core

    def _work_item_past_execute(self) -> WorkItem:
        item = WorkItem(id="w-gate", title="t", platform="opire", category="dev_bounty")
        item.phase = WorkPhase.EXECUTE
        item.add_checkpoint(WorkPhase.EXECUTE, {"executed": True})
        return item

    @pytest.mark.asyncio
    async def test_delivery_blocked_when_gate_fails(self):
        core = self._core_with_gate(gate_passed=False, autonomy_full=True)
        item = self._work_item_past_execute()
        # VALIDATE runs and fails the gate -> state ERROR.
        ok = await core._validate_work(item)
        assert ok is False
        assert item.state.value == "error"
        # DELIVER must also block because the latest VALIDATE checkpoint did not pass.
        delivered = await core._deliver_work(item)
        assert delivered is False
        assert "Quality Gate did not pass" in (item.error or "")

    @pytest.mark.asyncio
    async def test_delivery_allowed_when_gate_passes(self):
        core = self._core_with_gate(gate_passed=True, autonomy_full=True)
        item = self._work_item_past_execute()
        ok = await core._validate_work(item)
        assert ok is True
        # No evidence field set by fake? Fake returns passed=True regardless, so gate passes.
        delivered = await core._deliver_work(item)
        assert delivered is True


class TestPersistOneCheckpoint:
    """WorkerCore._persist_one_checkpoint writes to DB."""

    def test_persist_one_writes_row(self):
        core = WorkerCore(WorkerConfig(test_mode=True))
        item = WorkItem(id="persist-1", title="T", platform="hackerone", category="bug_bounty")
        item.phase = WorkPhase.SELECT
        item.add_checkpoint(WorkPhase.SELECT, {"selected": True})
        core._persist_one_checkpoint(item)
        cp = get_latest_checkpoint("persist-1")
        assert cp is not None
        assert str(cp.phase) == "select"
        data = checkpoint_data_dict(cp)
        assert data is not None
        assert data.get("selected") is True
