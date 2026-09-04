from __future__ import annotations

import asyncio
import pytest

from cores.worker_core import WorkerCore, WorkGoal, WorkerConfig, AutonomyLevel, WorkState, WorkPhase


class TestWorkerCore:
    @pytest.fixture
    def config(self):
        return WorkerConfig(autonomy_level=AutonomyLevel.PREPARE, test_mode=True)

    @pytest.fixture
    def goal(self):
        return WorkGoal(
            description="Generate income this month",
            target_monthly_usd=5000,
            max_hours_per_day=4,
            min_reward_usd=100,
            max_risk_score=0.5,
        )

    @pytest.fixture
    def core(self, config, goal):
        core = WorkerCore(config)
        core.set_goal(goal)
        return core

    @pytest.mark.asyncio
    async def test_worker_starts_and_stops(self, core):
        await core.start()
        assert core.state == WorkState.RUNNING

        await core.stop()
        assert core.state == WorkState.STOPPED

    @pytest.mark.asyncio
    async def test_worker_pause_resume(self, core):
        await core.start()
        await core.pause()
        assert core.state == WorkState.PAUSED

        await core.resume()
        assert core.state == WorkState.RUNNING

        await core.stop()

    @pytest.mark.asyncio
    async def test_worker_status(self, core):
        await core.start()
        await asyncio.sleep(0.05)

        status = core.get_status()
        assert status["state"] == "running"
        assert status["goal"] == "Generate income this month"
        assert status["goal_target_monthly_usd"] == 5000
        assert status["autonomy_level"] == "prepare"
        assert status["metrics"]["cycles_completed"] >= 0

        await core.stop()

    @pytest.mark.asyncio
    async def test_worker_goal_set(self, core):
        await core.start()
        assert core.current_goal is not None
        assert core.current_goal.description == "Generate income this month"
        assert core.current_goal.target_monthly_usd == 5000
        await core.stop()


class TestWorkGoal:
    def test_work_goal_creation(self):
        goal = WorkGoal(
            description="Test goal",
            target_monthly_usd=3000,
        )
        assert goal.description == "Test goal"
        assert goal.target_monthly_usd == 3000
        assert goal.max_hours_per_day == 4.0
        assert goal.min_reward_usd == 50.0
        assert goal.max_risk_score == 0.7
        assert goal.active is True


class TestWorkerConfig:
    def test_config_defaults(self):
        config = WorkerConfig()
        assert config.autonomy_level == AutonomyLevel.PREPARE
        assert config.checkpoint_interval_seconds == 300
        assert config.max_concurrent_work == 3
        assert config.discovery_interval_seconds == 1800
        assert config.human_approval_required is True
        assert config.safe_mode is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
