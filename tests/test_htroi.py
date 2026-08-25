"""HumanTimeAdjustedROI tests — Fase C (versioned formula)."""

from __future__ import annotations

from cores.direct_work_engine.economics import (
    HTROI_FORMULA_VERSION,
    compute_htroi,
)


class TestHTROICore:
    def test_basic_math(self) -> None:
        res = compute_htroi(expected_income_usd=100.0, human_hours=2.5)
        assert res.roi_usd_per_hour == 40.0
        assert res.formula_version == "HTROI-V1"

    def test_confidence_scales_income(self) -> None:
        res = compute_htroi(expected_income_usd=100.0, human_hours=2.0, confidence=0.5)
        assert res.roi_usd_per_hour == 25.0
        assert res.confidence_applied == 0.5

    def test_zero_hours_is_undefined_with_warning(self) -> None:
        res = compute_htroi(expected_income_usd=500.0, human_hours=0)
        assert res.roi_usd_per_hour is None
        assert any("human_hours" in w for w in res.warnings)


class TestAutomationCompression:
    def test_compression_only_with_measured_baseline(self) -> None:
        """§14: compression requires a real manual baseline — never invented."""
        no_baseline = compute_htroi(expected_income_usd=100.0, human_hours=1.0, automation_hours=0.4)
        assert no_baseline.compression_pct is None

    def test_compression_calculated(self) -> None:
        res = compute_htroi(
            expected_income_usd=100.0,
            human_hours=10 / 60,
            automation_hours=25 / 60,
            manual_baseline_hours=120 / 60,
        )
        # Spec §14 example: 120min manual -> 25min OWNEX = 79.2%? No: (120-25)/120
        assert res.compression_pct == 79.2

    def test_automation_ratio_vs_human_total(self) -> None:
        res = compute_htroi(
            expected_income_usd=100.0,
            human_hours=1 / 3,  # 20 min humanos (review)
            automation_hours=25 / 60,
            manual_baseline_hours=2.0,
        )
        assert res.automation_ratio is not None and res.automation_ratio > 1.0


def test_version_pinned() -> None:
    assert HTROI_FORMULA_VERSION == "HTROI-V1"
