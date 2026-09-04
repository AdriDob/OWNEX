"""Tests for Mission Controller and Store."""

from __future__ import annotations

import pytest

from core.mission.controller import (
    MissionController,
)
from core.mission.store import (
    get_mission_store,
)


@pytest.fixture()
def clean_store():
    """Provide a clean mission store for each test."""
    from database.db import Base, engine

    # Drop and recreate tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    store = get_mission_store()
    yield store
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def controller(clean_store):
    """Mission controller instance using test store."""

    # Create a new controller with the test store
    return MissionController(store=clean_store)


class TestMissionStore:
    """Tests for MissionStore."""

    def test_create_mission(self, clean_store):
        """Test creating a mission."""
        mission = clean_store.create(
            mission_id="test_mission_1",
            mission_type="security_pipeline",
            opportunity_id="opp-1",
            priority=10,
            expected_value_usd=500.0,
            payload={"target": "example.com"},
            context={"source": "test"},
            total_stages=7,
        )
        assert mission.mission_id == "test_mission_1"
        assert mission.mission_type == "security_pipeline"
        assert mission.status == "pending"
        assert mission.priority == 10
        assert mission.expected_value_usd == 500.0

    def test_get_mission(self, clean_store):
        """Test retrieving a mission."""
        clean_store.create(
            mission_id="test_mission_2",
            mission_type="dev_bounty",
            opportunity_id="opp-2",
        )
        mission = clean_store.get("test_mission_2")
        assert mission is not None
        assert mission.mission_id == "test_mission_2"
        assert mission.mission_type == "dev_bounty"

    def test_mission_not_found(self, clean_store):
        """Test getting non-existent mission returns None."""
        mission = clean_store.get("non_existent")
        assert mission is None

    def test_start_mission(self, clean_store):
        """Test starting a mission."""
        clean_store.create(mission_id="test_mission_3", mission_type="security_pipeline")
        mission = clean_store.start_mission("test_mission_3")
        assert mission.status == "running"
        assert mission.started_at is not None

    def test_advance_stage(self, clean_store):
        """Test advancing mission stage."""
        clean_store.create(
            mission_id="test_mission_4",
            mission_type="dev_bounty",
            total_stages=6,
        )
        clean_store.start_mission("test_mission_4")
        mission = clean_store.advance_stage("test_mission_4", "clone", 1, {"repo": "cloned"})
        assert mission.current_stage == "clone"
        assert mission.stage_order == 1
        assert mission.status == "running"

    def test_complete_mission(self, clean_store):
        """Test completing a mission."""
        clean_store.create(
            mission_id="test_mission_5",
            mission_type="security_pipeline",
            expected_value_usd=500.0,
        )
        clean_store.start_mission("test_mission_5")
        mission = clean_store.complete_mission("test_mission_5", 250.0, {"confirmed": True})
        assert mission.status == "completed"
        assert mission.actual_value_usd == 250.0
        assert mission.completed_at is not None

    def test_fail_mission(self, clean_store):
        """Test failing a mission."""
        clean_store.create(
            mission_id="test_mission_6",
            mission_type="dev_bounty",
            max_retries=3,
        )
        clean_store.start_mission("test_mission_6")
        mission = clean_store.fail_mission("test_mission_6", "Execution error")
        assert mission.status == "pending"  # Should retry
        assert mission.retry_count == 1

    def test_fail_mission_max_retries(self, clean_store):
        """Test failing mission with max retries reached."""
        clean_store.create(
            mission_id="test_mission_7",
            mission_type="dev_bounty",
            max_retries=1,
        )
        clean_store.start_mission("test_mission_7")
        # First failure
        clean_store.fail_mission("test_mission_7", "Error 1")
        # Second failure - should exceed max retries
        mission = clean_store.fail_mission("test_mission_7", "Error 2")
        assert mission.status == "failed"

    def test_block_unblock_mission(self, clean_store):
        """Test blocking and unblocking a mission."""
        clean_store.create(mission_id="test_mission_8", mission_type="dev_bounty")
        clean_store.start_mission("test_mission_8")

        blocked = clean_store.block_mission("test_mission_8", "Waiting for user approval")
        assert blocked.status == "blocked"
        assert blocked.error_message == "Waiting for user approval"

        unblocked = clean_store.unblock_mission("test_mission_8")
        assert unblocked.status == "running"

    def test_checkpoint_save_and_restore(self, clean_store):
        """Test saving and restoring checkpoints."""
        clean_store.create(
            mission_id="test_mission_9",
            mission_type="dev_bounty",
            total_stages=6,
        )
        clean_store.start_mission("test_mission_9")
        clean_store.advance_stage("test_mission_9", "clone", 1, {"repo": "cloned"})
        clean_store.advance_stage("test_mission_9", "analyze", 2, {"issue": "analyzed"})

        # Save checkpoint
        checkpoint = clean_store.save_checkpoint("test_mission_9", "analyze", 2, {"fix": "ready"}, {"source": "test"})
        assert checkpoint.stage == "analyze"
        assert checkpoint.stage_order == 2

        # Check checkpoint history
        checkpoints = clean_store.get_checkpoints("test_mission_9")
        assert len(checkpoints) >= 1
        assert checkpoints[-1].stage == "analyze"

        # Restore from checkpoint
        restored = clean_store.restore_from_checkpoint("test_mission_9")
        assert restored.current_stage == "analyze"
        assert restored.stage_order == 2


class TestMissionController:
    """Tests for MissionController."""

    def test_create_mission(self, controller):
        """Test creating a mission via controller."""
        result = controller.create_mission(
            mission_type="security_pipeline",
            opportunity_id="opp-1",
            priority=10,
            expected_value_usd=500.0,
            payload={"target": "example.com"},
            context={"source": "test"},
            total_stages=7,
        )
        assert result.success
        assert result.mission is not None
        assert result.mission.mission_type == "security_pipeline"
        assert result.mission.status == "pending"

    def test_start_mission(self, controller):
        """Test starting a mission."""
        result = controller.create_mission(
            mission_type="security_pipeline",
            opportunity_id="opp-1",
        )
        mid = result.mission.mission_id

        result = controller.start_mission(mid)
        assert result.success
        assert result.mission.status == "running"

    def test_advance_stage(self, controller):
        """Test advancing stage via controller."""
        result = controller.create_mission(
            mission_type="dev_bounty",
            total_stages=6,
        )
        mid = result.mission.mission_id
        controller.start_mission(mid)

        result = controller.advance_stage(mid, "clone", 1, {"repo": "cloned"})
        assert result.success
        assert result.mission.current_stage == "clone"
        assert result.mission.stage_order == 1

    def test_complete_mission(self, controller):
        """Test completing a mission."""
        result = controller.create_mission(
            mission_type="security_pipeline",
            expected_value_usd=500.0,
        )
        mid = result.mission.mission_id
        controller.start_mission(mid)
        controller.advance_stage(mid, "recon", 1, {})

        result = controller.complete_mission(mid, 250.0, {"confirmed": True})
        assert result.success
        assert result.mission.status == "completed"
        assert result.mission.actual_value_usd == 250.0

    def test_checkpoint_and_restore(self, controller):
        """Test checkpoint and restore via controller."""
        result = controller.create_mission(
            mission_type="dev_bounty",
            total_stages=6,
        )
        mid = result.mission.mission_id
        controller.start_mission(mid)
        controller.advance_stage(mid, "clone", 1, {"repo": "cloned"})
        controller.advance_stage(mid, "analyze", 2, {"issue": "analyzed"})
        controller.checkpoint(mid, "analyze", 2, {"fix": "ready"}, {"source": "test"})

        # Restore
        result = controller.restore_from_checkpoint(mid)
        assert result.success
        assert result.mission.current_stage == "analyze"
        assert result.mission.stage_order == 2

    def test_mission_summary(self, controller):
        """Test mission summary for dashboard."""
        controller.create_mission(mission_type="security_pipeline")
        controller.create_mission(mission_type="dev_bounty")
        controller.start_mission(controller.get_all_missions()[0].mission_id)

        summary = controller.get_mission_summary()
        assert "active_count" in summary
        assert "blocked_count" in summary
        assert "waiting_human_count" in summary
        assert "by_status" in summary


class TestMissionLifecycle:
    """Integration tests for full mission lifecycle."""

    def test_full_security_pipeline_lifecycle(self, controller):
        """Test complete security pipeline mission lifecycle."""
        # Create mission
        result = controller.create_mission(
            mission_type="security_pipeline",
            opportunity_id="target-1",
            priority=100,
            expected_value_usd=1000.0,
            total_stages=7,
        )
        assert result.success
        mid = result.mission.mission_id

        # Start pipeline
        result = controller.start_mission(mid)
        assert result.success

        # Simulate 7-stage pipeline
        stages = [
            ("recon", 1, {"endpoints": 15}),
            ("attack_surface", 2, {"surface": "mapped"}),
            ("hypothesis", 3, {"hypotheses": 5}),
            ("validation", 4, {"confirmed": 2}),
            ("evidence", 5, {"bundles": 2}),
            ("report", 6, {"report_id": "report-123"}),
            ("learning", 7, {"lessons": 3}),
        ]

        for i, (stage, order, result_data) in enumerate(stages):
            result = controller.advance_stage(mid, stage, order, result_data)
            assert result.success
            assert result.mission.current_stage == stage
            assert result.mission.stage_order == order

            # Save checkpoint at each stage
            checkpoint_result = controller.checkpoint(mid, stage, order, result_data, {"pipeline": "security"})
            assert checkpoint_result.success

        # Complete mission
        result = controller.complete_mission(mid, 750.0, {"findings": 2, "reports": 1})
        assert result.success
        assert result.mission.status == "completed"
        assert result.mission.actual_value_usd == 750.0

        # Verify checkpoints were saved
        from core.mission.store import get_mission_store

        store = get_mission_store()
        checkpoints = store.get_checkpoints(mid)
        assert len(checkpoints) == 7

    def test_recovery_from_checkpoint(self, controller):
        """Test recovering a mission from checkpoint after simulated crash."""
        result = controller.create_mission(
            mission_type="dev_bounty",
            opportunity_id="dev-opp-1",
            total_stages=6,
        )
        mid = result.mission.mission_id
        controller.start_mission(mid)
        controller.advance_stage(mid, "clone", 1, {"repo": "cloned"})
        controller.advance_stage(mid, "analyze", 2, {"issue": "analyzed"})
        controller.checkpoint(mid, "analyze", 2, {"issue": "analyzed"}, {"source": "test"})

        # Simulate crash and restore
        result = controller.restore_from_checkpoint(mid)
        assert result.success
        assert result.mission.current_stage == "analyze"
        assert result.mission.stage_order == 2

    def test_block_unblock(self, controller):
        """Test blocking and unblocking mission."""
        result = controller.create_mission(mission_type="dev_bounty")
        mid = result.mission.mission_id
        controller.start_mission(mid)

        # Block
        result = controller.block_mission(mid, "Waiting for user approval")
        assert result.success
        assert result.mission.status == "blocked"

        # Unblock
        result = controller.unblock_mission(mid)
        assert result.success
        assert result.mission.status == "running"

    def test_mission_summary(self, controller):
        """Test mission summary for dashboard."""
        controller.create_mission(mission_type="security_pipeline")
        controller.create_mission(mission_type="dev_bounty")
        mid = controller.get_all_missions()[0].mission_id
        controller.start_mission(mid)

        summary = controller.get_mission_summary()
        assert summary["active_count"] >= 1
        assert "by_status" in summary
        assert "stale_missions" in summary
