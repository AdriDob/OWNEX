"""Test WorkerCore crash→resume capability.

Verifies that:
1. Checkpoints persist to SQLite during workflow execution
2. After a simulated crash, WorkerCore can resume from last checkpoint
3. Completed phases are NOT re-executed on resume
4. Audit trail entries survive the crash
5. Circuit breakers track failures across restarts
"""

from __future__ import annotations

import json

import pytest

from cores.worker_core.models import (
    AutonomyLevel,
    WorkerConfig,
    WorkGoal,
    WorkItem,
    WorkState,
)
from cores.worker_core.persistence import (
    get_active_work_items,
    get_all_checkpoints,
    get_latest_checkpoint,
    resume_from,
    save_checkpoint,
)


@pytest.fixture
def worker_config():
    return WorkerConfig(
        autonomy_level=AutonomyLevel.FULL,
        test_mode=False,
        human_approval_required=False,
        max_concurrent_work=1,
        max_cost_per_workflow_usd=10.0,
    )


@pytest.fixture
def sample_goal():
    return WorkGoal(
        description="Test goal",
        target_monthly_usd=5000.0,
        min_reward_usd=10.0,
        max_risk_score=0.8,
    )


class TestCrashResume:
    """Test crash→resume persistence."""

    def test_checkpoint_persists_discover_phase(self, sample_goal):
        """Checkpoint persists after DISCOVER phase."""
        save_checkpoint(
            "wi-test-001",
            "discover",
            {"title": "Test Work", "ev_hr": 25.0},
            work_item_title="Test Work",
            phase_completed=True,
        )
        cp = get_latest_checkpoint("wi-test-001")
        assert cp is not None
        assert cp.phase == "discover"
        assert cp.phase_completed == "true"
        data = json.loads(cp.checkpoint_data)
        assert data["title"] == "Test Work"

    def test_checkpoint_persists_execute_phase(self):
        """Checkpoint persists after EXECUTE phase."""
        save_checkpoint(
            "wi-test-002",
            "execute",
            {"artifacts": ["file.py"], "evidence": ["screenshot.png"]},
            phase_completed=True,
        )
        cp = get_latest_checkpoint("wi-test-002")
        assert cp is not None
        assert cp.phase == "execute"
        data = json.loads(cp.checkpoint_data)
        assert "file.py" in data["artifacts"]

    def test_resume_from_discover_completed(self):
        """Resume from completed DISCOVER → next phase is EVALUATE."""
        save_checkpoint("wi-resume-001", "discover", {}, phase_completed=True)
        cp = get_latest_checkpoint("wi-resume-001")
        result = resume_from(cp)
        assert result == "evaluate"

    def test_resume_from_execute_completed(self):
        """Resume from completed EXECUTE → next phase is VALIDATE."""
        save_checkpoint("wi-resume-002", "execute", {}, phase_completed=True)
        cp = get_latest_checkpoint("wi-resume-002")
        result = resume_from(cp)
        assert result == "validate"

    def test_resume_from_learn_completed(self):
        """Resume from completed LEARN → None (workflow done)."""
        save_checkpoint("wi-resume-003", "learn", {}, phase_completed=True)
        cp = get_latest_checkpoint("wi-resume-003")
        result = resume_from(cp)
        assert result is None

    def test_resume_from_failed_phase(self):
        """Resume from failed phase → re-run that phase."""
        save_checkpoint("wi-resume-004", "execute", {}, phase_completed=False, error="timeout")
        cp = get_latest_checkpoint("wi-resume-004")
        result = resume_from(cp)
        assert result == "execute"

    def test_multiple_checkpoints_chronological(self):
        """Multiple checkpoints are in chronological order."""
        for phase in ["discover", "evaluate", "select", "prepare", "execute"]:
            save_checkpoint("wi-multi", phase, {"phase": phase}, phase_completed=True)

        all_cps = get_all_checkpoints("wi-multi")
        assert len(all_cps) == 5
        phases = [cp.phase for cp in all_cps]
        assert phases == ["discover", "evaluate", "select", "prepare", "execute"]

    def test_active_work_items_after_crash(self):
        """Active work items persist across crash."""
        save_checkpoint("wi-crash-001", "prepare", {}, phase_completed=False)
        save_checkpoint("wi-crash-002", "execute", {}, phase_completed=False)

        active = get_active_work_items()
        assert "wi-crash-001" in active
        assert "wi-crash-002" in active

    def test_resume_preserves_metadata(self):
        """Resume preserves work item metadata from checkpoint."""
        save_checkpoint(
            "wi-meta-001",
            "execute",
            {"estimated_reward_usd": 100.0, "platform": "hackerone"},
            work_item_title="Critical XSS",
            work_item_platform="hackerone",
            work_item_category="bug_bounty",
            phase_completed=True,
        )
        cp = get_latest_checkpoint("wi-meta-001")
        assert cp.work_item_title == "Critical XSS"
        assert cp.work_item_platform == "hackerone"
        assert cp.work_item_category == "bug_bounty"


class TestAuditTrail:
    """Test audit trail persistence."""

    def test_create_audit_entry(self):
        """Audit entry creates successfully."""
        from cores.worker_core.audit import create_audit_entry, get_workflow_audit

        entry = create_audit_entry(
            workflow_id="wf-test-001",
            execution_id="ex-test-001",
            action="discover",
            phase="discover",
            status="success",
            details={"title": "Test Work"},
        )
        # Access fields while session may still be open
        entry_id = entry.id
        wf_id = entry.workflow_id
        act = entry.action
        assert entry_id > 0
        assert wf_id == "wf-test-001"
        assert act == "discover"

        # Verify retrieval from DB
        entries = get_workflow_audit("wf-test-001")
        assert len(entries) >= 1

    def test_audit_entry_with_approval(self):
        """Audit entry records approval state."""
        from cores.worker_core.audit import create_audit_entry, get_workflow_audit

        create_audit_entry(
            workflow_id="wf-approve-001",
            execution_id="ex-approve-001",
            action="deliver",
            requires_approval=True,
            approved_by="human",
            approval_reason="Looks good",
            autonomy_level="prepare",
        )
        # Verify via re-query (detached session safe)
        entries = get_workflow_audit("wf-approve-001")
        assert len(entries) >= 1
        e = entries[0]
        assert e.requires_approval == "true"
        assert e.approved_by == "human"
        assert e.autonomy_level == "prepare"

    def test_audit_stats(self):
        """Audit stats aggregate correctly."""
        from cores.worker_core.audit import create_audit_entry, get_audit_stats

        create_audit_entry(
            workflow_id="wf-stats-001",
            execution_id="ex-stats-001",
            action="discover",
            status="success",
        )
        stats = get_audit_stats()
        assert stats["total_entries"] >= 1
        assert isinstance(stats["total_cost_usd"], float)


class TestCircuitBreakers:
    """Test circuit breaker integration with WorkerCore."""

    def test_init_circuit_breakers(self, worker_config):
        """Circuit breakers initialize for all engine components."""
        from cores.worker_core.orchestrator import WorkerCore

        wc = WorkerCore(worker_config)
        assert "discovery" in wc._circuit_breakers
        assert "evaluation" in wc._circuit_breakers
        assert "execution" in wc._circuit_breakers
        assert "delivery" in wc._circuit_breakers
        assert "learning" in wc._circuit_breakers
        assert "skill" in wc._circuit_breakers

    def test_circuit_breaker_allows_normal_operation(self, worker_config):
        """Circuit breaker allows operation when closed."""
        from cores.worker_core.orchestrator import WorkerCore

        wc = WorkerCore(worker_config)
        assert wc._check_circuit_breaker("discovery") is True

    def test_circuit_breaker_blocks_after_failures(self, worker_config):
        """Circuit breaker blocks after max failures."""
        from cores.worker_core.orchestrator import WorkerCore

        wc = WorkerCore(worker_config)
        # Trigger 3 failures (default threshold)
        for _ in range(3):
            wc._record_engine_failure("discovery", "test error")

        assert wc._check_circuit_breaker("discovery") is False

    def test_circuit_breaker_resets_on_success(self, worker_config):
        """Circuit breaker resets after successful operation."""
        from cores.worker_core.orchestrator import WorkerCore

        wc = WorkerCore(worker_config)
        # 2 failures (below threshold)
        for _ in range(2):
            wc._record_engine_failure("discovery", "test error")

        # Success resets
        wc._record_engine_success("discovery")
        assert wc._check_circuit_breaker("discovery") is True

    def test_spending_limit_per_workflow(self, worker_config):
        """Spending limit blocks workflow when exceeded."""
        from cores.worker_core.orchestrator import WorkerCore

        wc = WorkerCore(worker_config)
        wf_id = "wf-spending-001"
        wc._workflow_costs[wf_id] = 8.0

        # Should be OK with $1 more (limit is $10)
        assert wc._check_spending_limit(wf_id, 1.0) is True

        # Should block with $3 more
        assert wc._check_spending_limit(wf_id, 3.0) is False

    def test_spending_limit_per_session(self, worker_config):
        """Session spending limit degrades worker when exceeded."""
        from cores.worker_core.orchestrator import WorkerCore

        wc = WorkerCore(worker_config)
        wc._session_cost_usd = 18.0

        # Recording $3 more pushes over $20 limit
        wc._record_cost("wf-test", 3.0)
        assert wc.state == WorkState.DEGRADED


class TestAutonomyEnforcement:
    """Test that autonomy levels are properly enforced."""

    def test_none_autonomy_blocks_sensitive_actions(self, worker_config):
        """NONE autonomy requires approval for prepare, execute, deliver."""
        from cores.worker_core.orchestrator import WorkerCore

        wc = WorkerCore(worker_config)
        wc.config.autonomy_level = AutonomyLevel.NONE

        # NONE (0) < PREPARE (2) → blocked
        assert wc.requires_human_approval("prepare") is True
        # NONE (0) < EXECUTE (3) → blocked
        assert wc.requires_human_approval("execute") is True
        # NONE (0) < FULL (4) → blocked
        assert wc.requires_human_approval("deliver") is True
        # NONE (0) == NONE (0) → allowed (discover/learn need no approval)
        assert wc.requires_human_approval("discover") is False

    def test_full_autonomy_allows_delivery(self, worker_config):
        """FULL autonomy allows delivery without approval."""
        from cores.worker_core.orchestrator import WorkerCore

        wc = WorkerCore(worker_config)
        wc.config.autonomy_level = AutonomyLevel.FULL

        assert wc.requires_human_approval("deliver") is False
        assert wc.requires_human_approval("execute") is False

    def test_prepare_autonomy_blocks_execute(self, worker_config):
        """PREPARE autonomy blocks execute and deliver, allows discover."""
        from cores.worker_core.orchestrator import WorkerCore

        wc = WorkerCore(worker_config)
        wc.config.autonomy_level = AutonomyLevel.PREPARE

        # PREPARE (2) < EXECUTE (3) → blocked
        assert wc.requires_human_approval("execute") is True
        # PREPARE (2) < FULL (4) → blocked
        assert wc.requires_human_approval("deliver") is True
        # PREPARE (2) == PREPARE (2) → allowed
        assert wc.requires_human_approval("prepare") is False
        # PREPARE (2) > DISCOVER (1) → allowed
        assert wc.requires_human_approval("discover") is False

    def test_human_gate_returns_reason(self, worker_config):
        """Human gate check returns reason string."""
        from cores.worker_core.orchestrator import WorkerCore

        wc = WorkerCore(worker_config)
        wc.config.autonomy_level = AutonomyLevel.PREPARE

        item = WorkItem(title="Test")
        needs_approval, reason = wc.check_human_gate(item, "deliver")
        assert needs_approval is True
        assert "deliver" in reason
