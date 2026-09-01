"""Tests for Computer Use Learning System."""

from __future__ import annotations

from cores.computer_use.learning import (
    ComputerUseLearner,
    FieldPosition,
    FillRecord,
    PlatformLearning,
    get_computer_use_learner,
)

# ── FieldPosition ────────────────────────────────────────────────


class TestFieldPosition:
    def test_success_rate(self):
        fp = FieldPosition(field_name="title", times_used=10, times_succeeded=8)
        assert fp.success_rate == 0.8

    def test_success_rate_zero_uses(self):
        fp = FieldPosition(field_name="title")
        assert fp.success_rate == 0.0

    def test_to_dict(self):
        fp = FieldPosition(field_name="email", x=100, y=200, confidence=0.9)
        d = fp.to_dict()
        assert d["field_name"] == "email"
        assert d["x"] == 100
        assert d["y"] == 200
        assert d["confidence"] == 0.9
        assert d["times_used"] == 0
        assert d["success_rate"] == 0.0


# ── FillRecord ───────────────────────────────────────────────────


class TestFillRecord:
    def test_to_dict(self):
        r = FillRecord(
            id="fill_abc123",
            platform="outlier",
            task="fill form",
            success=True,
            fields_filled=[{"name": "response", "value": "test"}],
            field_positions=[FieldPosition(field_name="response")],
            duration_ms=5000.0,
            steps_taken=3,
        )
        d = r.to_dict()
        assert d["id"] == "fill_abc123"
        assert d["platform"] == "outlier"
        assert d["success"] is True
        assert len(d["field_positions"]) == 1
        assert d["duration_ms"] == 5000.0


# ── PlatformLearning ─────────────────────────────────────────────


class TestPlatformLearning:
    def test_success_rate(self):
        pl = PlatformLearning(platform="outlier", total_attempts=10, successful_fills=7)
        assert pl.success_rate == 0.7

    def test_success_rate_zero(self):
        pl = PlatformLearning(platform="outlier")
        assert pl.success_rate == 0.0

    def test_to_dict(self):
        pl = PlatformLearning(platform="outlier", total_attempts=5, successful_fills=3)
        d = pl.to_dict()
        assert d["platform"] == "outlier"
        assert d["total_attempts"] == 5
        assert d["successful_fills"] == 3
        assert d["success_rate"] == 0.6


# ── ComputerUseLearner ───────────────────────────────────────────


class TestComputerUseLearner:
    def test_singleton(self):
        l1 = get_computer_use_learner()
        l2 = get_computer_use_learner()
        assert l1 is l2

    def test_record_success(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        record = learner.record_success(
            platform="outlier",
            task="fill form",
            fields=[{"name": "response", "value": "test"}],
            duration_ms=5000.0,
            steps=3,
        )
        assert record.success is True
        assert record.platform == "outlier"
        assert record.duration_ms == 5000.0

    def test_record_failure(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        record = learner.record_failure(
            platform="outlier",
            task="fill form",
            error="Screenshot failed",
            duration_ms=1000.0,
            steps=1,
        )
        assert record.success is False
        assert record.error == "Screenshot failed"

    def test_platform_stats_after_success(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        learner.record_success(platform="outlier", task="t", fields=[], duration_ms=5000, steps=3)
        learner.record_success(platform="outlier", task="t", fields=[], duration_ms=3000, steps=2)

        stats = learner.get_platform_stats("outlier")
        assert stats is not None
        assert stats["total_attempts"] == 2
        assert stats["successful_fills"] == 2
        assert stats["success_rate"] == 1.0
        assert stats["avg_duration_ms"] == 4000.0

    def test_platform_stats_after_failure(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        learner.record_success(platform="outlier", task="t", fields=[], duration_ms=5000, steps=3)
        learner.record_failure(platform="outlier", task="t", error="timeout")

        stats = learner.get_platform_stats("outlier")
        assert stats["total_attempts"] == 2
        assert stats["successful_fills"] == 1
        assert stats["failed_fills"] == 1
        assert stats["success_rate"] == 0.5
        assert len(stats["common_errors"]) == 1

    def test_get_best_positions(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        # Record multiple successes with the same field position
        for _ in range(3):
            fp = FieldPosition(
                field_name="title",
                x=100,
                y=200,
                confidence=0.8,
            )
            learner.record_success(
                platform="outlier",
                task="t",
                fields=[],
                positions=[fp],
            )

        best = learner.get_best_positions("outlier")
        assert "title" in best
        assert best["title"].x == 100
        assert best["title"].times_used >= 2

    def test_get_recommendation_no_data(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        rec = learner.get_recommendation("outlier")
        assert rec["status"] == "no_data"
        assert "No historical data" in rec["recommendation"]

    def test_get_recommendation_reliable(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        for _ in range(10):
            learner.record_success(platform="outlier", task="t", fields=[], duration_ms=3000, steps=2)

        rec = learner.get_recommendation("outlier")
        assert rec["status"] == "reliable"
        assert rec["success_rate"] == 1.0
        assert rec["total_attempts"] == 10

    def test_get_recommendation_moderate(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        for _ in range(5):
            learner.record_success(platform="outlier", task="t", fields=[], duration_ms=3000, steps=2)
        for _ in range(5):
            learner.record_failure(platform="outlier", task="t", error="fail")

        rec = learner.get_recommendation("outlier")
        assert rec["status"] == "moderate"
        assert rec["success_rate"] == 0.5

    def test_get_recommendation_unreliable(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        learner.record_success(platform="outlier", task="t", fields=[], duration_ms=3000, steps=2)
        for _ in range(9):
            learner.record_failure(platform="outlier", task="t", error="fail")

        rec = learner.get_recommendation("outlier")
        assert rec["status"] == "unreliable"
        assert rec["success_rate"] == 0.1

    def test_should_use_cached_positions(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        assert learner.should_use_cached_positions("outlier") is False

        # Add 2 reliable positions with enough uses
        for name in ("email", "password"):
            for _ in range(3):
                fp = FieldPosition(
                    field_name=name,
                    confidence=0.8,
                )
                learner.record_success(platform="outlier", task="t", fields=[], positions=[fp])

        assert learner.should_use_cached_positions("outlier") is True

    def test_get_records(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        learner.record_success(platform="outlier", task="t1", fields=[], duration_ms=1000, steps=1)
        learner.record_failure(platform="outlier", task="t2", error="e")
        learner.record_success(platform="mindrift", task="t3", fields=[], duration_ms=2000, steps=2)

        # All records
        all_recs = learner.get_records()
        assert len(all_recs) == 3

        # Filter by platform
        outlier_recs = learner.get_records(platform="outlier")
        assert len(outlier_recs) == 2

        mindrift_recs = learner.get_records(platform="mindrift")
        assert len(mindrift_recs) == 1

    def test_persistence(self, tmp_path):
        # Record some data
        learner1 = ComputerUseLearner(data_dir=tmp_path)
        learner1.record_success(platform="outlier", task="t", fields=[], duration_ms=5000, steps=3)

        # Reload and verify
        learner2 = ComputerUseLearner(data_dir=tmp_path)
        stats = learner2.get_platform_stats("outlier")
        assert stats is not None
        assert stats["total_attempts"] == 1
        assert stats["successful_fills"] == 1

    def test_get_all_stats(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        learner.record_success(platform="outlier", task="t", fields=[])
        learner.record_success(platform="mindrift", task="t", fields=[])

        all_stats = learner.get_all_stats()
        assert len(all_stats) == 2
        platforms = {s["platform"] for s in all_stats}
        assert "outlier" in platforms
        assert "mindrift" in platforms

    def test_best_duration_tracking(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        learner.record_success(platform="outlier", task="t", fields=[], duration_ms=10000, steps=5)
        learner.record_success(platform="outlier", task="t", fields=[], duration_ms=3000, steps=2)

        stats = learner.get_platform_stats("outlier")
        assert stats["best_duration_ms"] == 3000.0
        assert stats["avg_duration_ms"] == 6500.0

    def test_common_errors_limited(self, tmp_path):
        learner = ComputerUseLearner(data_dir=tmp_path)
        for i in range(15):
            learner.record_failure(platform="outlier", task="t", error=f"error_{i}")

        stats = learner.get_platform_stats("outlier")
        assert len(stats["common_errors"]) <= 10  # capped at 10
