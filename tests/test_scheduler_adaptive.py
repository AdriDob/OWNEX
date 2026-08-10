"""Tests for the adaptive scheduler timing + priority logic in api/scheduler.py.

SELF-3 — api/scheduler.py was rewritten without tests. These cover the two
pure, DB-free adaptive pieces: stage cooldown (`_should_run`) and the
RewardLearner-backed tech adjustment (`_compute_tech_adjustment`).
DB/rate-limit integration needs live DB + RewardLearner data, so it is left to
integration coverage (like the CSRF tests stay isolated).
"""

from __future__ import annotations

import pytest

from api.scheduler import (
    STAGE_INTERVALS,
    TARGET_COOLDOWN,
    ScanScheduler,
    _compute_tech_adjustment,
)


@pytest.fixture
def sched() -> ScanScheduler:
    return ScanScheduler(interval_minutes=30)


class TestShouldRun:
    @pytest.mark.parametrize("stage", list(STAGE_INTERVALS))
    def test_uses_stage_interval_when_never_run(self, sched: ScanScheduler, stage: str) -> None:
        # last_run defaults to 0; any now >= interval must schedule.
        assert sched._should_run(stage, now=STAGE_INTERVALS[stage]) is True

    @pytest.mark.parametrize("stage", list(STAGE_INTERVALS))
    def test_scheduled_recently_skipped(self, sched: ScanScheduler, stage: str) -> None:
        interval = STAGE_INTERVALS[stage]
        now = 1_000_000.0
        sched._last_run[stage] = now
        # Just under the interval must NOT run.
        assert sched._should_run(stage, now=now + interval - 1) is False

    @pytest.mark.parametrize("stage", list(STAGE_INTERVALS))
    def test_scheduled_after_interval_runs(self, sched: ScanScheduler, stage: str) -> None:
        interval = STAGE_INTERVALS[stage]
        now = 1_000_000.0
        sched._last_run[stage] = now
        assert sched._should_run(stage, now=now + interval) is True

    def test_unknown_stage_falls_back_to_scheduler_interval(self, sched: ScanScheduler) -> None:
        # Unknown stage -> uses self.interval (30 min default).
        assert sched._should_run("not_a_stage", now=sched.interval) is True
        sched._last_run["not_a_stage"] = 1_000_000.0
        assert sched._should_run("not_a_stage", now=1_000_000.0 + sched.interval - 1) is False
        assert sched._should_run("not_a_stage", now=1_000_000.0 + sched.interval) is True


class TestCooldownConstant:
    def test_target_cooldown_one_hour(self) -> None:
        assert TARGET_COOLDOWN == 3600


class TestComputeTechAdjustment:
    def test_empty_tags_return_baseline(self) -> None:
        assert _compute_tech_adjustment("", {}) == 1.0
        assert _compute_tech_adjustment("  ", {"idor": 2.0}) == 1.0

    def test_no_matching_adjustments(self) -> None:
        # A known tech tag but no adjustments recorded for any of its vulns.
        result = _compute_tech_adjustment("django", {})
        assert result == 1.0

    def test_matches_best_vuln_adjustment(self) -> None:
        # django -> idor, sqli, xss. Give differing adjustments; pick the max.
        adjustments = {"idor": 1.5, "sqli": 3.0, "xss": 2.0}
        assert _compute_tech_adjustment("django", adjustments) == pytest.approx(3.0)

    def test_partial_vuln_covered(self) -> None:
        # graphql -> idor, injection, auth_bypass. Only idor has an adjustment.
        result = _compute_tech_adjustment("graphql", {"idor": 4.2})
        assert result == pytest.approx(4.2)

    def test_multiple_tags_pick_global_best(self) -> None:
        # django (idor/sqli/xss) + aws (ssrf). ssrf gives the highest adj.
        adjustments = {"idor": 1.0, "sqli": 1.2, "ssrf": 5.5, "xss": 1.3}
        assert _compute_tech_adjustment("django aws", adjustments) == pytest.approx(5.5)

    def test_no_baseline_1_0_when_all_adj_below_one(self) -> None:
        # Adjustments worse than baseline do NOT lower the score below 1.0.
        adjustments = {"idor": 0.5, "sqli": 0.2}
        result = _compute_tech_adjustment("django", adjustments)
        assert result == pytest.approx(1.0)

    def test_case_insensitive_lookup(self) -> None:
        adjustments = {"xss": 2.5}
        assert _compute_tech_adjustment("Django WordPress", adjustments) == pytest.approx(2.5)
