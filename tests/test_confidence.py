"""Confidence Engine tests — Fase E (versioned, spec §26)."""

from __future__ import annotations

from cores.direct_work_engine.economics import (
    CONFIDENCE_FORMULA_VERSION,
    compute_confidence,
)


class TestBands:
    def test_all_inputs_known_and_strong_is_high(self) -> None:
        res = compute_confidence(source_reliability=95, data_freshness_days=5, historical_samples=10)
        assert res.band == "HIGH"
        assert res.score >= 70

    def test_unknown_inputs_force_unknown_band(self) -> None:
        res = compute_confidence()  # todo desconocido
        assert res.band == "UNKNOWN"
        assert len(res.warnings) >= 2

    def test_weak_inputs_degrade_to_low(self) -> None:
        res = compute_confidence(
            source_reliability=30,
            data_freshness_days=200,
            historical_samples=0,
            missing_fields=3,
        )
        assert res.band == "LOW"
        assert res.score < 45


class TestPenalties:
    def test_each_penalty_is_documented(self) -> None:
        res = compute_confidence(missing_fields=1)
        assert any("campos críticos" in w for w in res.warnings)

    def test_freshness_thresholds(self) -> None:
        mid = compute_confidence(data_freshness_days=45)
        old = compute_confidence(data_freshness_days=120)
        assert any("(-15)" in w for w in mid.warnings)
        assert any("(-30)" in w for w in old.warnings)

    def test_clamped_to_valid_range(self) -> None:
        res = compute_confidence(source_reliability=0, data_freshness_days=365, missing_fields=9)
        assert 0 <= res.score <= 100


def test_version_pinned() -> None:
    assert CONFIDENCE_FORMULA_VERSION == "CONF-V1"
