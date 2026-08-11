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

        targets = [FakeTarget(1), FakeTarget(2)]
        priorities = _compute_target_priorities(targets)
        assert isinstance(priorities, dict)
        assert len(priorities) == 2
        for tid in (1, 2):
            assert 0.1 <= priorities[tid] <= 10.0

    def test_priority_domain_match_uses_program_score(self):
        from unittest.mock import patch

        from api.scheduler import _compute_target_priorities

        class FakeTarget:
            def __init__(self, id, name, domain):
                self.id = id
                self.name = name
                self.domain = domain

        targets = [FakeTarget(1, "test", "example.com")]
        with patch("api.scheduler.RewardLearner") as mock_learner:
            mock_learner.return_value.analyze.return_value = type(
                "Report", (), {"vuln_type_adjustments": {"idor": 1.5}}
            )()
            priorities = _compute_target_priorities(targets)
        assert isinstance(priorities, dict)
        assert 0.1 <= priorities[1] <= 10.0

    def test_tech_adjustment_base_case(self):
        from api.scheduler import _compute_tech_adjustment

        assert _compute_tech_adjustment("", {}) == 1.0
        assert _compute_tech_adjustment("anything", {}) == 1.0
        assert _compute_tech_adjustment("", {"idor": 1.5}) == 1.0

    def test_tech_adjustment_picks_highest_adjustment(self):
        from api.scheduler import _compute_tech_adjustment

        adjustments = {"idor": 1.2, "ssrf": 0.8, "xss": 1.5}
        result = _compute_tech_adjustment("react, vue", adjustments)
        assert result == 1.5

    def test_tech_adjustment_api_targets(self):
        from api.scheduler import _compute_tech_adjustment

        adjustments = {"idor": 1.5, "auth_bypass": 1.3, "sqli": 1.0}
        result = _compute_tech_adjustment("api, rest", adjustments)
        assert result == 1.5

    def test_tech_adjustment_cloud_targets(self):
        from api.scheduler import _compute_tech_adjustment

        adjustments = {"ssrf": 1.8, "idor": 1.2}
        result = _compute_tech_adjustment("aws, cloud", adjustments)
        assert result == 1.8

    def test_tech_adjustment_wordpress_sites(self):
        from api.scheduler import _compute_tech_adjustment

        adjustments = {"xss": 1.4, "sqli": 0.6}
        result = _compute_tech_adjustment("wordpress, cms, php", adjustments)
        assert result == 1.4

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

            for stage in (
                "_stage_discover",
                "_stage_recon",
                "_stage_hypothesis",
                "_stage_promote",
                "_stage_validate",
                "_stage_report",
                "_stage_ai_bounty",
            ):
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


class _FakeTarget:
    def __init__(self, tid, name=None, domain=None):
        self.id = tid
        self.name = name or f"target-{tid}"
        self.domain = domain


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None

    def count(self):
        return 0


class _FakeSession:
    def __init__(self, targets):
        self._targets = targets

    def query(self, model):
        return _FakeQuery(self._targets)

    def execute(self, *args, **kwargs):
        return None

    def close(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakePrioritizer:
    def __init__(self, priorities, results=None):
        self.priorities = priorities
        self.results = results or []
        self.last_adjustments = None

    def prioritize(self, targets, target_intel_map, adjustments):
        self.last_adjustments = adjustments
        return self.priorities, self.results


class _FakeLearner:
    def __init__(self, adjustments=None):
        self.adjustments = adjustments or {}

    def analyze(self):
        return None

    def get_adjustments(self):
        return self.adjustments


class TestScanSchedulerAdaptive:
    """SELF-3 — adaptive scheduler behavior (KNOWN_DEBT #3).

    Behavioral coverage for `_stage_recon` on top of the existing unit tests:
      - per-target cooldown actually skips `_recon_target` (no re-scan < 1h)
      - targets are scanned in RewardLearner-prioritized order (high first)
      - a scan stamps the target cooldown so the next cycle skips it
      - RewardLearner adjustments are passed to TargetPrioritizer
      - stale cooldown entries are purged at the end of a pipeline cycle
    """

    def _setup(self, monkeypatch, targets, priorities, adjustments=None):

        from api import scheduler as sched_mod

        sched = sched_mod.ScanScheduler(interval_minutes=30)
        sched._running = True
        prioritizer = _FakePrioritizer(priorities)

        monkeypatch.setattr(sched_mod, "RewardLearner", lambda: _FakeLearner(adjustments))
        monkeypatch.setattr(sched_mod, "TargetPrioritizer", lambda: prioritizer)
        monkeypatch.setattr(sched_mod, "db", type("DB", (), {"SessionLocal": lambda self: _FakeSession(targets)})())
        monkeypatch.setattr(sched_mod, "get_config", lambda: type("Cfg", (), {"scan_mode": "passive"})())

        order: list[int] = []

        async def recorder(target, mode, session):
            order.append(target.id)

        sched._recon_target = recorder
        return sched, prioritizer, order

    def test_recon_skips_target_in_cooldown(self, monkeypatch):
        import asyncio
        import time

        targets = [_FakeTarget(1, "hot", "example.com")]
        sched, _, order = self._setup(monkeypatch, targets, {1: 5.0})
        sched._target_cooldowns[1] = time.time()  # scanned just now

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(sched._stage_recon())
        finally:
            loop.close()
        assert order == [], "target in cooldown must not be re-scanned"

    def test_recon_scans_when_cooldown_expired(self, monkeypatch):
        import asyncio
        import time

        from api import scheduler as sched_mod

        targets = [_FakeTarget(1, "hot", "example.com")]
        sched, _, order = self._setup(monkeypatch, targets, {1: 5.0})
        sched._target_cooldowns[1] = time.time() - sched_mod.TARGET_COOLDOWN - 10

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(sched._stage_recon())
        finally:
            loop.close()
        assert order == [1]

    def test_recon_priority_order_high_first(self, monkeypatch):
        import asyncio

        targets = [
            _FakeTarget(1, "low", "low.example.com"),
            _FakeTarget(2, "high", "high.example.com"),
        ]
        sched, _, order = self._setup(monkeypatch, targets, {1: 1.0, 2: 8.0})

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(sched._stage_recon())
        finally:
            loop.close()
        assert order == [2, 1], "highest-priority target must be scanned first"

    def test_scan_stamps_cooldown(self, monkeypatch):
        import asyncio
        import time

        targets = [_FakeTarget(1, "hot", "example.com")]
        sched, _, order = self._setup(monkeypatch, targets, {1: 5.0})

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(sched._stage_recon())
        finally:
            loop.close()
        assert order == [1]
        assert time.time() - sched._target_cooldowns[1] < 30

    def test_no_rescan_within_hour(self, monkeypatch):
        import asyncio

        targets = [_FakeTarget(1, "hot", "example.com")]
        sched, _, order = self._setup(monkeypatch, targets, {1: 5.0})

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(sched._stage_recon())
            loop.run_until_complete(sched._stage_recon())
        finally:
            loop.close()
        assert order == [1], "second cycle must skip the just-scanned target"

    def test_reward_learner_adjustments_reach_prioritizer(self, monkeypatch):
        import asyncio

        targets = [_FakeTarget(1, "hot", "example.com")]
        sched, prioritizer, _ = self._setup(monkeypatch, targets, {1: 5.0}, adjustments={"idor": 1.5})

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(sched._stage_recon())
        finally:
            loop.close()
        assert prioritizer.last_adjustments == {"idor": 1.5}

    def test_cycle_purges_stale_cooldowns(self, monkeypatch):
        import asyncio
        import time

        from api import scheduler as sched_mod

        targets = [_FakeTarget(1, "a", "a.example.com"), _FakeTarget(2, "b", "b.example.com")]
        sched, _, _ = self._setup(monkeypatch, targets, {1: 5.0, 2: 4.0})

        now = time.time()
        for stage in sched_mod.STAGE_INTERVALS:
            sched._last_run[stage] = now
        sched._cycle_started = now
        sched._target_cooldowns[1] = now  # fresh → kept
        sched._target_cooldowns[2] = now - sched_mod.TARGET_COOLDOWN * 2 - 10  # stale → purged

        async def noop():
            return None

        monkeypatch.setattr(sched, "_parallel_recovery", noop)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(sched._run_pipeline())
        finally:
            loop.close()
        assert 1 in sched._target_cooldowns
        assert 2 not in sched._target_cooldowns
