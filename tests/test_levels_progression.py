"""L8: hunter levels — XP only from verified outcomes, thresholds, ledger."""

from __future__ import annotations

import pytest

from cores.levels import (
    LEVELS,
    XP_TABLE,
    ProgressionEngine,
    get_progression_engine,
    reset_progression_engine,
)


def _engine(tmp_path) -> ProgressionEngine:
    reset_progression_engine()
    return ProgressionEngine(tmp_path / "xp.jsonl")


class TestXpTable:
    def test_only_verified_events_grant_xp(self):
        assert set(XP_TABLE) == {
            "task_completed",
            "stage_completed",
            "finding_confirmed",
            "opportunity_delivered",
            "report_accepted",
            "milestone_hit",
            "payout_received",
        }

    def test_payout_worth_most(self):
        assert XP_TABLE["payout_received"] > XP_TABLE["finding_confirmed"]
        assert XP_TABLE["finding_confirmed"] > XP_TABLE["task_completed"]

    def test_unknown_event_raises_never_invents(self, tmp_path):
        with pytest.raises(ValueError, match="unknown XP event"):
            _engine(tmp_path).award("clicked_button")


class TestLevels:
    def test_fresh_starts_at_level_1(self, tmp_path):
        lv = _engine(tmp_path).level()
        assert (lv.level, lv.title, lv.total_xp) == (1, "Novato", 0)
        assert lv.next_threshold == 100

    def test_thresholds_ascending_and_capped_at_10(self, tmp_path):
        thresholds = [t for _, _, t in LEVELS]
        assert thresholds == sorted(thresholds)
        assert len(LEVELS) == 10

    def test_award_accumulates_and_levels_up(self, tmp_path):
        eng = _engine(tmp_path)
        eng.award("finding_confirmed")  # +25
        eng.award("finding_confirmed")  # +25
        eng.award("task_completed")  # +10 → 60
        assert eng.total_xp() == 60
        assert eng.level().level == 1
        eng.award("report_accepted")  # +50 → 110
        lv = eng.level()
        assert lv.level == 2 and lv.title == "Aprendiz"
        assert lv.next_threshold == 250

    def test_max_level_caps(self, tmp_path):
        eng = _engine(tmp_path)
        for _ in range(200):
            eng.award("payout_received")
        lv = eng.level()
        assert lv.level == 10 and lv.next_threshold is None and lv.pct_to_next == 100.0

    def test_persistence_across_instances(self, tmp_path):
        _engine(tmp_path).award("milestone_hit", ref_id="m-100")
        eng2 = ProgressionEngine(tmp_path / "xp.jsonl")
        assert eng2.total_xp() == 75

    def test_history_and_summary(self, tmp_path):
        eng = _engine(tmp_path)
        eng.award("task_completed", ref_id="t-1")
        eng.award("payout_received", ref_id="p-1")
        assert len(eng.history()) == 2
        s = eng.summary()
        assert s["total_xp"] == 110 and s["events"] == {"task_completed": 1, "payout_received": 1}

    def test_singleton_reset(self, tmp_path):
        get_progression_engine(tmp_path / "xp.jsonl").award("task_completed")
        reset_progression_engine()
        assert get_progression_engine(tmp_path / "other.jsonl").total_xp() == 0
