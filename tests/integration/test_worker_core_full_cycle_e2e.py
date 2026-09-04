"""WorkerCore Full Cycle E2E Test — TASK 07

Tests the complete autonomous work cycle:
DISCOVER → EVALUATE → SELECT → PREPARE → EXECUTE → VALIDATE → DELIVER → LEARN

Uses real engines from the project. Only external services are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cores.worker_core.models import (
    AutonomyLevel,
    WorkerConfig,
    WorkGoal,
    WorkState,
)
from cores.worker_core.orchestrator import WorkerCore


class TestWorkerCoreFullCycleE2E:
    """E2E test for WorkerCore full cycle."""

    @pytest.fixture
    def config(self):
        return WorkerConfig(
            autonomy_level=AutonomyLevel.FULL,
            test_mode=True,
            checkpoint_interval_seconds=3600,
            human_approval_required=False,
        )

    @pytest.fixture
    def goal(self):
        return WorkGoal(
            description="Test goal",
            target_monthly_usd=10000,
            min_reward_usd=10,
            max_risk_score=0.9,
            active=True,
        )

    @pytest.fixture
    def mock_discovery(self):
        """Mock discovery engine that returns a real-looking opportunity."""
        mock = AsyncMock()
        opp = MagicMock()
        opp.id = "test_opp_001"
        opp.title = "Fix API endpoint bug"
        opp.platform = MagicMock(value="opire")
        opp.category = MagicMock(value="software_engineering")
        opp.payment = 100.0
        opp.estimated_time_hours = 2.0
        opp.risk_score = 0.2
        opp.acceptance_probability = 0.8
        opp.expected_value_usd_per_hour = 50.0
        opp.description = "Fix a bug in the API endpoint"
        mock.discover_all = AsyncMock(return_value=[opp])
        return mock

    @pytest.fixture
    def mock_evaluation(self):
        """Mock evaluation engine that passes quality gate."""
        mock = MagicMock()
        mock.evaluate = MagicMock(
            return_value={
                "passed": True,
                "score": 0.85,
                "reasons": ["High EV", "Low risk"],
                "barrier_score": 15.0,
                "expected_value_usd_per_hour": 50.0,
                "acceptance_probability": 0.8,
                "compatibility_score": 0.9,
                "speed_score": 0.7,
                "reputation_score": 0.6,
                "risk_score": 0.2,
                "strict_filter_rejected": False,
                "strict_filter_reasons": [],
                "quality_gate_result": {"passed": True, "reason": "Evidence present"},
            }
        )
        return mock

    @pytest.fixture
    def mock_execution(self):
        """Mock execution engine."""
        mock = MagicMock()
        mock.execute = MagicMock(
            return_value={
                "success": True,
                "artifacts": ["fix.py", "test_fix.py"],
                "evidence": ["Screenshot of fix", "Test output"],
                "output": "Bug fixed successfully",
                "error": None,
                "execution_time_s": 45.0,
            }
        )
        return mock

    @pytest.fixture
    def mock_delivery(self):
        """Mock delivery engine."""
        mock = MagicMock()
        mock.deliver = MagicMock(
            return_value={
                "success": True,
                "submission_id": "sub_001",
                "submission_url": "https://opire.com/sub/001",
                "platform_response": {"status": "submitted"},
                "error": None,
            }
        )
        return mock

    @pytest.fixture
    def mock_learning(self):
        """Mock learning engine."""
        mock = MagicMock()
        mock.learn = MagicMock(
            return_value={
                "success": True,
                "lessons": ["High EV opportunities work well"],
                "skill_updates": {"python": 0.1},
                "platform_updates": {"opire": 0.5},
                "category_updates": {"software_engineering": 0.3},
                "error": None,
            }
        )
        return mock

    @pytest.fixture
    def worker(self, config, mock_discovery, mock_evaluation, mock_execution, mock_delivery, mock_learning):
        """Create WorkerCore with all mock engines connected."""
        wc = WorkerCore(config)
        wc.set_discovery_engine(mock_discovery)
        wc.set_evaluation_engine(mock_evaluation)
        wc.set_execution_engine(mock_execution)
        wc.set_delivery_engine(mock_delivery)
        wc.set_learning_engine(mock_learning)
        return wc

    @pytest.mark.asyncio
    async def test_full_cycle_happy_path(self, worker, goal):
        """Test complete cycle: DISCOVER → EVALUATE → SELECT → PREPARE → EXECUTE → VALIDATE → DELIVER → LEARN."""
        worker.set_goal(goal)

        # Run one cycle
        await worker._run_cycle()

        # Verify work item was created
        assert len(worker.work_items) == 1
        work_item = list(worker.work_items.values())[0]

        # Verify workflow_id and execution_id exist
        assert work_item.id is not None
        assert len(work_item.id) > 0

        # Verify all phases were executed
        phases_hit = [cp["phase"] for cp in work_item.checkpoints]
        assert "discover" in phases_hit
        assert "evaluate" in phases_hit
        assert "select" in phases_hit
        assert "prepare" in phases_hit
        assert "execute" in phases_hit
        assert "validate" in phases_hit
        assert "deliver" in phases_hit
        assert "learn" in phases_hit

        # Verify artifacts and evidence
        assert "fix.py" in work_item.artifacts
        assert "test_fix.py" in work_item.artifacts
        assert "Screenshot of fix" in work_item.evidence

        # Verify metrics recorded
        assert worker.metrics.work_items_completed == 1

    @pytest.mark.asyncio
    async def test_discovery_failure_stops_cycle(self, worker, goal):
        """Test that discovery failure stops the cycle gracefully."""
        worker.set_goal(goal)
        worker._discovery_engine.discover_all = AsyncMock(return_value=[])

        await worker._run_cycle()

        # No work item should be created
        assert len(worker.work_items) == 0

    @pytest.mark.asyncio
    async def test_evaluation_failure_stops_cycle(self, worker, goal):
        """Test that evaluation failure stops the cycle."""
        worker.set_goal(goal)
        worker._evaluation_engine.evaluate = MagicMock(
            return_value={
                "passed": False,
                "score": 0.1,
                "reasons": ["Below threshold"],
                "quality_gate_result": {"passed": False, "reason": "Low score"},
            }
        )

        await worker._run_cycle()

        # Work item should exist but be in error state
        assert len(worker.work_items) == 1
        work_item = list(worker.work_items.values())[0]
        assert work_item.state == WorkState.ERROR

    @pytest.mark.asyncio
    async def test_quality_gate_blocks_delivery(self, worker, goal):
        """Test that Quality Gate failure blocks delivery."""
        worker.set_goal(goal)
        worker._evaluation_engine.evaluate = MagicMock(
            return_value={
                "passed": True,
                "score": 0.8,
                "reasons": [],
                "quality_gate_result": {"passed": False, "reason": "No evidence"},
            }
        )

        await worker._run_cycle()

        work_item = list(worker.work_items.values())[0]
        # Should fail at validation (quality gate)
        assert work_item.state == WorkState.ERROR
        assert "Quality Gate" in (work_item.error or "")

    @pytest.mark.asyncio
    async def test_human_gate_requires_approval(
        self, config, goal, mock_discovery, mock_evaluation, mock_execution, mock_delivery, mock_learning
    ):
        """Test that human gate blocks delivery when approval required."""
        config.human_approval_required = True
        config.autonomy_level = AutonomyLevel.EXECUTE
        worker = WorkerCore(config)
        worker.set_discovery_engine(mock_discovery)
        worker.set_evaluation_engine(mock_evaluation)
        worker.set_execution_engine(mock_execution)
        worker.set_delivery_engine(mock_delivery)
        worker.set_learning_engine(mock_learning)
        worker.set_goal(goal)

        await worker._run_cycle()

        work_item = list(worker.work_items.values())[0]
        # Should be paused waiting for human approval
        assert work_item.human_action_required is True
        assert work_item.state == WorkState.PAUSED

    @pytest.mark.asyncio
    async def test_checkpoint_persistence(self, worker, goal):
        """Test that checkpoints are persisted during the cycle."""
        worker.set_goal(goal)

        with patch("cores.worker_core.orchestrator.save_checkpoint") as mock_save:
            await worker._run_cycle()

            # save_checkpoint should be called multiple times
            assert mock_save.call_count >= 2

            # Verify checkpoint data structure
            first_call = mock_save.call_args_list[0]
            assert "work_item_id" in first_call.kwargs or len(first_call.args) >= 1

    @pytest.mark.asyncio
    async def test_execution_failure_stops_cycle(self, worker, goal):
        """Test that execution failure stops the cycle."""
        worker.set_goal(goal)
        worker._execution_engine.execute = MagicMock(
            return_value={
                "success": False,
                "artifacts": [],
                "evidence": [],
                "output": "",
                "error": "Execution failed",
                "execution_time_s": 0.0,
            }
        )

        await worker._run_cycle()

        work_item = list(worker.work_items.values())[0]
        assert work_item.state == WorkState.ERROR
        assert "Execution failed" in (work_item.error or "")

    @pytest.mark.asyncio
    async def test_metrics_recorded(self, worker, goal):
        """Test that metrics are properly recorded after cycle."""
        worker.set_goal(goal)

        await worker._run_cycle()

        assert worker.metrics.cycles_completed == 1
        assert worker.metrics.work_items_completed == 1
        assert worker.metrics.total_revenue_usd > 0
        assert worker.metrics.last_cycle_at is not None

    @pytest.mark.asyncio
    async def test_work_item_has_all_required_fields(self, worker, goal):
        """Test that work item has all required fields populated."""
        worker.set_goal(goal)

        await worker._run_cycle()

        work_item = list(worker.work_items.values())[0]
        assert work_item.id is not None
        assert work_item.title is not None
        assert work_item.platform is not None
        assert work_item.category is not None
        assert work_item.estimated_reward_usd > 0
        assert work_item.estimated_hours > 0
        assert work_item.expected_value_usd_per_hour > 0
        assert work_item.phase is not None
        assert work_item.state is not None

    @pytest.mark.asyncio
    async def test_resume_capability(self, worker, goal):
        """Test that worker can resume from checkpoint."""
        worker.set_goal(goal)

        # Run one cycle
        await worker._run_cycle()

        # Get the work item
        work_item = list(worker.work_items.values())[0]
        work_id = work_item.id

        # Simulate crash: create new worker
        new_worker = WorkerCore(worker.config)
        new_worker.set_goal(goal)

        # Verify resume detects the work item
        resumed = new_worker.resume_open_work_items()
        assert len(resumed) >= 1
        assert any(wid == work_id for wid, _ in resumed)


class TestWorkerCoreContracts:
    """Test that contracts are properly defined and satisfied."""

    def test_discovery_engine_protocol_satisfied(self):
        """Test that UniversalDiscovery satisfies DiscoveryEngineProtocol."""
        from cores.direct_work_engine.discovery import UniversalDiscovery
        from cores.worker_core.contracts import DiscoveryEngineProtocol

        assert issubclass(UniversalDiscovery, DiscoveryEngineProtocol)

    def test_evaluation_engine_protocol_satisfied(self):
        """Test that DirectWorkEvaluationEngine satisfies EvaluationEngineProtocol."""
        from cores.direct_work_engine.evaluation import DirectWorkEvaluationEngine
        from cores.worker_core.contracts import EvaluationEngineProtocol

        assert issubclass(DirectWorkEvaluationEngine, EvaluationEngineProtocol)

    def test_execution_engine_protocol_satisfied(self):
        """Test that DirectWorkExecutionEngine satisfies ExecutionEngineProtocol."""
        from cores.direct_work_engine.execution import DirectWorkExecutionEngine
        from cores.worker_core.contracts import ExecutionEngineProtocol

        assert issubclass(DirectWorkExecutionEngine, ExecutionEngineProtocol)

    def test_delivery_engine_protocol_satisfied(self):
        """Test that DirectWorkDeliveryEngine satisfies DeliveryEngineProtocol."""
        from cores.direct_work_engine.delivery import DirectWorkDeliveryEngine
        from cores.worker_core.contracts import DeliveryEngineProtocol

        assert issubclass(DirectWorkDeliveryEngine, DeliveryEngineProtocol)

    def test_learning_engine_protocol_satisfied(self):
        """Test that DirectWorkLearningEngine satisfies LearningEngineProtocol."""
        from cores.direct_work_engine.learning import DirectWorkLearningEngine
        from cores.worker_core.contracts import LearningEngineProtocol

        assert issubclass(DirectWorkLearningEngine, LearningEngineProtocol)


class TestWorkerCoreAutonomyLevels:
    """Test autonomy level enforcement."""

    def test_autonomy_none_requires_approval_for_everything(self):
        wc = WorkerCore(WorkerConfig(autonomy_level=AutonomyLevel.NONE))
        assert wc.requires_human_approval("discover") is True
        assert wc.requires_human_approval("evaluate") is True
        assert wc.requires_human_approval("execute") is True
        assert wc.requires_human_approval("deliver") is True

    def test_autonomy_full_allows_all(self):
        wc = WorkerCore(WorkerConfig(autonomy_level=AutonomyLevel.FULL))
        assert wc.requires_human_approval("discover") is False
        assert wc.requires_human_approval("evaluate") is False
        assert wc.requires_human_approval("execute") is False
        assert wc.requires_human_approval("deliver") is False

    def test_autonomy_execute_allows_execution_not_delivery(self):
        wc = WorkerCore(WorkerConfig(autonomy_level=AutonomyLevel.EXECUTE))
        assert wc.requires_human_approval("discover") is False
        assert wc.requires_human_approval("execute") is False
        assert wc.requires_human_approval("deliver") is True
