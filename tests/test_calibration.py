"""Calibration loop tests — Income Multiplier Fase D (spec §13)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cores.direct_work_engine.calibration import CalibrationEngine


@pytest.fixture()
def engine(tmp_path: Path) -> CalibrationEngine:
    return CalibrationEngine(store_path=tmp_path / "learning" / "calibration.jsonl")


class TestRecordAndPersist:
    def test_prediction_persists_jsonl(self, engine: CalibrationEngine) -> None:
        rec = engine.record(platform="outlier", predicted_hourly=15.0)
        assert rec.actual_hourly is None
        lines = engine.store_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["platform"] == "outlier"

    def test_resolution_records_error_pct(self, engine: CalibrationEngine) -> None:
        engine.record(platform="outlier", predicted_hourly=40.0)
        rec = engine.record(platform="outlier", predicted_hourly=40.0, actual_hourly=12.0)
        assert rec.error_pct == -70.0  # spec §13 example: overpromise


class TestPlatformFactor:
    def test_insufficient_data_is_neutral(self, engine: CalibrationEngine) -> None:
        for i in range(2):  # < MIN_SAMPLES=3
            engine.record(
                platform="opire",
                predicted_hourly=10.0,
                actual_hourly=20.0 + i,
            )
        factor, confidence = engine.platform_factor("opire")
        assert factor == 1.0
        assert confidence == "insufficient_data"

    def test_factor_reflects_reality_clamped(self, engine: CalibrationEngine) -> None:
        # Reality pays ~half of prediction → factor should drop near 0.5 clamp
        for real in (5.0, 6.0, 5.5):
            engine.record(platform="opire", predicted_hourly=12.0, actual_hourly=real)
        factor, confidence = engine.platform_factor("opire")
        assert 0.45 <= factor <= 0.55
        assert confidence in ("medium", "high")

    def test_overpromise_never_grows_unbounded(self, engine: CalibrationEngine) -> None:
        for _ in range(4):
            engine.record(platform="x", predicted_hourly=1.0, actual_hourly=99.0)
        factor, _ = engine.platform_factor("x")
        assert factor <= 2.0  # clamp superior


class TestDashboardFeed:
    def test_worst_overpromises_dedupes_by_platform(self, engine: CalibrationEngine) -> None:
        engine.record(platform="a", predicted_hourly=10.0)
        engine.record(platform="a", predicted_hourly=10.0, actual_hourly=1.0)
        engine.record(platform="b", predicted_hourly=10.0)
        engine.record(platform="b", predicted_hourly=10.0, actual_hourly=9.0)
        worst = engine.worst_overpromises()
        assert worst[0].platform == "a"  # -90% peor que -10%
        assert len(worst) == 2


def test_survives_corrupt_line(tmp_path: Path) -> None:
    store = tmp_path / "cal.jsonl"
    good = (
        '{"platform":"p","predicted_hourly":10.0,"actual_hourly":11.0,'
        '"predicted_income_usd":null,"actual_income_usd":null,'
        '"opportunity_id":null,"error_pct":10.0,"recorded_at":"t"}'
    )
    store.write_text(good + "\n{CORRUPT}\n", encoding="utf-8")
    eng = CalibrationEngine(store_path=store)
    assert len(eng.resolved_for_platform("p")) == 1
