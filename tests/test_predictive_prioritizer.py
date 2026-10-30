"""Tests for the Predictive Target Prioritizer (cores/learning/predictive_prioritizer.py)."""

from __future__ import annotations

import pytest

from cores.learning.predictive_prioritizer import (
    PredictivePrioritizer,
    clamp,
    predict_targets,
)


@pytest.fixture()
def pp(tmp_path, monkeypatch):
    p = PredictivePrioritizer(data_dir=tmp_path)
    return p


def test_clamp_bounds():
    assert clamp(0.0) == 0.05
    assert clamp(1.0) == 0.95
    assert clamp(0.5) == 0.5


def test_forecast_rank_shape(pp):
    result = predict_targets(
        [
            {"id": "t1", "name": "A", "platform": "bugcrowd", "reward": 5000, "hours": 8, "last_finding_days_ago": 2},
            {"id": "t2", "name": "B", "platform": "opire", "reward": 150, "hours": 1, "last_finding_days_ago": 20},
        ]
    )
    assert result["horizon_days"] == 7
    assert len(result["ranked"]) == 2
    assert result["top_pick"] is not None
    # Rewards differ enough that the 5000-valued target wins on EV/hour
    assert result["top_pick"]["target_id"] == "t1"


def test_unknown_acceptance_is_explicit(pp):
    result = pp.forecast([{"id": "x", "name": "X", "platform": "custom", "reward": 100, "hours": 2}])
    rank = result["ranked"][0]
    assert rank["acceptance_source"] == "unknown"
    assert rank["acceptance_probability"] == 0.5
    assert "UNKNOWN" in rank["reasoning"]


def test_empirical_acceptance_when_history(pp, monkeypatch):
    from cores.learning import predictive_prioritizer as mod

    # Seed per-platform outcome history (bugcrowd: 4 wins / 5 samples)
    monkeypatch.setattr(
        mod.PredictivePrioritizer,
        "_platform_outcomes",
        lambda self: {"bugcrowd": {"accepted": 4, "rejected": 1, "samples": 5, "acceptance": 0.8}},
    )
    monkeypatch.setattr(mod.PredictivePrioritizer, "_velocity_days", lambda self: {"bugcrowd": 20.0})
    result = pp.forecast([{"id": "t", "name": "T", "platform": "bugcrowd", "reward": 1000, "hours": 4}])
    rank = result["ranked"][0]
    assert rank["acceptance_source"] == "empirical"
    assert rank["acceptance_probability"] == pytest.approx(0.8)
    assert rank["velocity_days"] == pytest.approx(20.0)
    assert rank["confidence"] in ("medium", "high")


def test_rejected_history_lowers_acceptance(pp, monkeypatch):
    from cores.learning import predictive_prioritizer as mod

    monkeypatch.setattr(
        mod.PredictivePrioritizer,
        "_platform_outcomes",
        lambda self: {"hackerone": {"accepted": 1, "rejected": 4, "samples": 5, "acceptance": 0.2}},
    )
    result = pp.forecast([{"id": "t", "name": "T", "platform": "hackerone", "reward": 1000, "hours": 4}])
    assert result["ranked"][0]["acceptance_probability"] == pytest.approx(0.2)


def test_forecast_persists_and_loads(pp):
    pp.forecast([{"id": "t", "name": "T", "platform": "opire", "reward": 100, "hours": 2}])
    latest = pp.latest_forecast()
    assert latest is not None
    assert latest["top_pick"]["target_id"] == "t"


def test_singleton():
    assert PredictivePrioritizer.__name__ == "PredictivePrioritizer"
    from cores.learning.predictive_prioritizer import get_predictive_prioritizer

    assert get_predictive_prioritizer() is get_predictive_prioritizer()
