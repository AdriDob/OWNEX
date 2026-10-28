"""LAYA adapter + calibration + pilot-C confidence nudge.

No torch/weights needed: the adapter runs on an injected fake backend.
Real-model paths are tested only as honest UNAVAILABLE.
"""

from __future__ import annotations

from typing import Any

import pytest

from cores.ai.laya_adapter import (
    LayaAdapter,
    LayaQuestion,
    LayaUnavailable,
    finding_questions,
    finding_state,
)
from cores.ai.laya_calibration import (
    apply_temperature,
    calibrate_decision,
    ece,
    fit_temperature,
    load_temperatures,
    save_temperatures,
)
from cores.validation.confidence import ConfidenceScorer, _laya_nudge


def _fake_backend(state, payload):
    out = []
    for q in payload:
        if q["kind"] == "choice":
            out.append(
                {
                    "label": q["options"][0],
                    "probability": 0.7,
                    "probabilities": {o: (0.7 if o == q["options"][0] else 0.3 / 4) for o in q["options"]},
                    "confidence": 0.7,
                }
            )
        elif q["kind"] == "noul":
            out.append({"probability": 0.8, "confidence": 0.8})
        else:
            out.append({"score": 3.0, "confidence": 0.6})
    return out


# ── Adapter availability ──────────────────────────────────────────


def test_unavailable_without_package(monkeypatch):
    monkeypatch.delenv("LAYA_DISABLED", raising=False)
    adapter = LayaAdapter()
    assert adapter.check() is False
    st = adapter.status()
    assert st["available"] is False and st["chat"] is False
    assert st["reason"]
    with pytest.raises(LayaUnavailable):
        adapter.decide("state", [LayaQuestion(name="q", kind="noul")])


def test_disabled_env(monkeypatch):
    monkeypatch.setenv("LAYA_DISABLED", "1")
    adapter = LayaAdapter(backend=_fake_backend)
    assert adapter.check() is False


def test_fake_backend_happy_path():
    adapter = LayaAdapter(backend=_fake_backend)
    assert adapter.check() is True
    d = adapter.decide("state", finding_questions({"vuln_type": "idor"}))
    assert len(d.answers) == 2
    assert d.by_name("credibility") is not None
    assert d.calibrated is False


# ── Fail-closed validation ────────────────────────────────────────


def test_empty_state_rejected():
    with pytest.raises(ValueError):
        LayaAdapter(backend=_fake_backend).decide("  ", [LayaQuestion(name="q", kind="noul")])


def test_too_many_options_rejected():
    qs = [LayaQuestion(name="big", kind="choice", options=[f"o{i}" for i in range(21)])]
    with pytest.raises(ValueError):
        LayaAdapter(backend=_fake_backend).decide("state", qs)


def test_unknown_kind_rejected():
    with pytest.raises(ValueError):
        LayaAdapter(backend=_fake_backend).decide("state", [LayaQuestion(name="q", kind="chat")])


def test_finding_questions_bounded():
    qs = finding_questions({})
    assert len(qs) == 2
    choice = next(q for q in qs if q.kind == "choice")
    assert 2 <= len(choice.options) <= 20
    assert finding_state({"vuln_type": "xss"}) != ""


# ── Calibration ───────────────────────────────────────────────────


def test_fit_needs_data():
    assert fit_temperature([], []) == 1.0
    assert fit_temperature([[0.9, 0.1]], [0]) == 1.0  # single class → no fit


def test_fit_finds_temperature():
    probs = [[0.6, 0.4]] * 6 + [[0.4, 0.6]] * 6
    labels = [0] * 6 + [1] * 6
    t = fit_temperature(probs, labels)
    assert isinstance(t, float) and 0.2 <= t <= 5.0


def test_apply_identity_at_default():
    p = {"a": 0.7, "b": 0.3}
    assert apply_temperature(p, 1.0) == p


def test_ece_empty_zero():
    assert ece([], []) == 0.0


def test_calibrate_marks_only_fitted():
    adapter = LayaAdapter(backend=_fake_backend)
    d = adapter.decide("state", finding_questions({}))
    out = calibrate_decision(d, {"severity_signal": 0.5})
    sev = out.by_name("severity_signal")
    cred = out.by_name("credibility")
    assert sev is not None and sev.calibrated is True
    assert cred is not None and cred.calibrated is False
    assert out.calibrated is True


def test_temperature_roundtrip(tmp_path):
    p = save_temperatures({"credibility": 0.7}, path=tmp_path / "t.json")
    assert load_temperatures(path=p) == {"credibility": 0.7}
    assert load_temperatures(path=tmp_path / "missing.json") == {}


# ── Pilot C: confidence nudge ─────────────────────────────────────


def test_nudge_rules():
    assert _laya_nudge(None) == 0.0
    assert _laya_nudge("garbage") == 0.0  # type: ignore[arg-type]
    assert _laya_nudge({"credibility": 0.9, "calibrated": False}) == 0.0
    assert _laya_nudge({"credibility": None, "calibrated": True}) == 0.0
    assert _laya_nudge({"credibility": 1.0, "calibrated": True}) == 0.05
    assert _laya_nudge({"credibility": 0.0, "calibrated": True}) == -0.05
    assert _laya_nudge({"credibility": 0.5, "calibrated": True}) == 0.0


def _scoring_inputs() -> Any:
    from types import SimpleNamespace
    from typing import Any as _Any

    results: _Any = [SimpleNamespace(consistent=True, has_rate_limit=False, has_timeout=False)]
    validation: _Any = SimpleNamespace(passed_rules=["r1", "r2"])
    return results, validation, {"risk_score": 50}


def test_confidence_default_unchanged():
    scorer = ConfidenceScorer()
    results, validation, signals = _scoring_inputs()
    base = scorer.calculate(results, validation, signals)
    assert base.breakdown["laya_signal"] == 0.0
    assert base.breakdown["uncertainty_penalty"] == 0.0


def test_confidence_calibrated_nudge_bounded():
    scorer = ConfidenceScorer()
    results, validation, signals = _scoring_inputs()
    base = scorer.calculate(results, validation, signals)
    up = scorer.calculate(results, validation, signals, laya_signal={"credibility": 1.0, "calibrated": True})
    down = scorer.calculate(results, validation, signals, laya_signal={"credibility": 0.0, "calibrated": True})
    assert up.score - base.score == pytest.approx(0.05)
    assert base.score - down.score == pytest.approx(0.05)
    assert up.breakdown["laya_signal"] == 0.05


def test_confidence_uncalibrated_inert():
    scorer = ConfidenceScorer()
    results, validation, signals = _scoring_inputs()
    base = scorer.calculate(results, validation, signals)
    same = scorer.calculate(results, validation, signals, laya_signal={"credibility": 0.99, "calibrated": False})
    assert same.score == base.score
