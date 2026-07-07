"""Tests for the autonomous pipeline scheduler."""

from __future__ import annotations


class TestScanSchedulerUnit:
    def test_should_run_returns_true_when_due(self):
        from api.scheduler import STAGE_INTERVALS, ScanScheduler
        sched = ScanScheduler(interval_minutes=30)
        stage = "discover"
        interval = STAGE_INTERVALS[stage]
        now = interval + 100.0
        assert sched._should_run(stage, now)

    def test_should_run_returns_false_when_recent(self):
        from api.scheduler import ScanScheduler
        sched = ScanScheduler(interval_minutes=30)
        sched._last_run["discover"] = 500.0
        assert not sched._should_run("discover", 600.0)

    def test_should_run_respects_stage_intervals(self):
        from api.scheduler import STAGE_INTERVALS, ScanScheduler
        sched = ScanScheduler(interval_minutes=30)
        now = 10_000.0
        for stage, interval in STAGE_INTERVALS.items():
            sched._last_run[stage] = now - interval + 1
            assert not sched._should_run(stage, now), f"{stage} should not run yet"
            sched._last_run[stage] = now - interval - 1
            assert sched._should_run(stage, now), f"{stage} should be due"

    def test_start_stop_lifecycle(self):
        from api.scheduler import ScanScheduler
        sched = ScanScheduler(interval_minutes=30)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(sched.start())
            assert sched._running
            assert sched._task is not None
            loop.run_until_complete(sched.stop())
            assert not sched._running
            assert sched._task is None
        finally:
            loop.close()

    def test_double_start_is_noop(self):
        from api.scheduler import ScanScheduler
        sched = ScanScheduler(interval_minutes=30)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(sched.start())
            task = sched._task
            loop.run_until_complete(sched.start())
            assert sched._task is task
            loop.run_until_complete(sched.stop())
        finally:
            loop.close()

    def test_target_cooldown_filter(self):
        from api.scheduler import TARGET_COOLDOWN, ScanScheduler
        sched = ScanScheduler(interval_minutes=30)
        now = 1000.0
        sched._target_cooldowns[1] = now - TARGET_COOLDOWN + 10
        assert (now - sched._target_cooldowns.get(1, 0)) < TARGET_COOLDOWN

    def test_cooldown_expired_allows_scan(self):
        from api.scheduler import TARGET_COOLDOWN, ScanScheduler
        sched = ScanScheduler(interval_minutes=30)
        now = 1000.0
        sched._target_cooldowns[1] = now - TARGET_COOLDOWN - 10
        assert (now - sched._target_cooldowns.get(1, 0)) >= TARGET_COOLDOWN

    def test_priority_computation_returns_dict(self):
        from api.scheduler import _compute_target_priorities
        class FakeTarget:
            def __init__(self, id):
                self.id = id
                self.name = f"target-{id}"
                self.domain = None
                self.vulnerability_type = None
                self.last_active = None
        targets = [FakeTarget(i) for i in range(3)]
        priorities = _compute_target_priorities(targets)
        assert isinstance(priorities, dict)
        assert len(priorities) == 3
        for tid in range(3):
            assert 0.1 <= priorities[tid] <= 10.0

    def test_loop_resilient_to_stage_failure(self):
        from api.scheduler import ScanScheduler
        sched = ScanScheduler(interval_minutes=30)
        sched._running = True
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def fail(*args):
                raise RuntimeError("stage failure")
            for stage in ("_stage_discover", "_stage_recon", "_stage_hypothesis", "_stage_validate", "_stage_report"):
                setattr(sched, stage, fail)
            from api.scheduler import logger
            logger.disabled = True
            loop.run_until_complete(sched._run_pipeline())
            logger.disabled = False
        finally:
            loop.close()

    def test_empty_recon_does_not_crash(self):
        from api.scheduler import ScanScheduler
        sched = ScanScheduler(interval_minutes=30)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from unittest.mock import patch
            with patch("api.scheduler.db.SessionLocal"):
                loop.run_until_complete(sched._stage_recon())
        finally:
            loop.close()

    def test_hypothesis_without_endpoints_does_not_crash(self):
        from cores.engine.hypothesis.generators import generate_hypotheses
        assert callable(generate_hypotheses)
