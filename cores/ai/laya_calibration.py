"""LAYA calibration — trust only temperatures fit on OWN data.

Upstream ships over-confident (mean ECE ~0.47 raw). Their own docs recommend
refitting one temperature per (question type, option count): ECE 0.47 → 0.08.
So: no calibrated temperature from OUR outcomes → probabilities stay
UNCALIBRATED and must be treated as ordering signals only, never as P(valid).

Pure stdlib, no numpy/torch. Temperatures persist as JSON {name: temp} with an
injectable path (tests never touch the real home).
"""

from __future__ import annotations

import json
import logging
import math
import os
from pathlib import Path

from cores.ai.laya_adapter import LayaAnswer, LayaDecision

logger = logging.getLogger("ownex.ai.laya_calibration")

DEFAULT_TEMPERATURE = 1.0
_T_GRID = [round(0.2 + 0.1 * i, 1) for i in range(49)]  # 0.2 .. 5.0


def _softmax(logits: list[float], temperature: float) -> list[float]:
    t = max(temperature, 1e-6)
    scaled = [v / t for v in logits]
    m = max(scaled)
    exps = [math.exp(v - m) for v in scaled]
    s = sum(exps) or 1.0
    return [e / s for e in exps]


def _probs_to_logits(probs: list[float]) -> list[float]:
    eps = 1e-9
    return [math.log(min(max(p, eps), 1.0 - eps)) for p in probs]


def _nll(probs_list: list[list[float]], labels: list[int], temperature: float) -> float:
    total = 0.0
    for probs, lab in zip(probs_list, labels, strict=True):
        cal = _softmax(_probs_to_logits(probs), temperature)
        total += -math.log(max(cal[lab], 1e-12))
    return total / max(len(labels), 1)


def fit_temperature(probs_list: list[list[float]], labels: list[int]) -> float:
    """Grid-search the NLL-minimizing temperature. Pure, deterministic.

    Returns DEFAULT_TEMPERATURE when there is nothing to learn from
    (empty, single class, or degenerate inputs) — never invents a fit.
    """
    if len(probs_list) < 2 or len(set(labels)) < 2:
        return DEFAULT_TEMPERATURE
    try:
        best_t, best_nll = DEFAULT_TEMPERATURE, _nll(probs_list, labels, DEFAULT_TEMPERATURE)
        for t in _T_GRID:
            nll = _nll(probs_list, labels, t)
            if nll < best_nll:
                best_nll, best_t = nll, t
        return best_t
    except Exception:
        return DEFAULT_TEMPERATURE


def apply_temperature(probs: dict[str, float], temperature: float) -> dict[str, float]:
    """Rescale a label→prob mapping. Identity at 1.0."""
    if not probs or temperature == DEFAULT_TEMPERATURE:
        return dict(probs)
    names = list(probs.keys())
    cal = _softmax(_probs_to_logits([probs[k] for k in names]), temperature)
    return dict(zip(names, cal, strict=True))


def ece(probs_list: list[list[float]], labels: list[int], bins: int = 10) -> float:
    """Expected Calibration Error of top-prob predictions. 0.0 when empty."""
    if not probs_list or bins < 1:
        return 0.0
    sums = [0.0] * bins
    hits = [0] * bins
    counts = [0] * bins
    for probs, lab in zip(probs_list, labels, strict=False):
        top = max(range(len(probs)), key=lambda i: probs[i])
        conf = probs[top]
        b = min(int(conf * bins), bins - 1)
        sums[b] += conf
        hits[b] += 1 if top == lab else 0
        counts[b] += 1
    total = sum(counts) or 1
    return sum((counts[b] / total) * abs(sums[b] / counts[b] - hits[b] / counts[b]) for b in range(bins) if counts[b])


def calibrate_decision(decision: LayaDecision, temperatures: dict[str, float]) -> LayaDecision:
    """Return a calibrated copy. Answers without a fitted temp stay UNCALIBRATED."""
    out: list[LayaAnswer] = []
    any_cal = False
    for a in decision.answers:
        t = temperatures.get(a.name)
        if a.probabilities and t and t != DEFAULT_TEMPERATURE:
            cal = apply_temperature(a.probabilities, t)
            top = max(cal, key=lambda k: cal[k])
            out.append(
                LayaAnswer(
                    name=a.name,
                    kind=a.kind,
                    label=top if a.kind == "choice" else a.label,
                    probability=cal[top] if a.kind == "choice" else a.probability,
                    score=a.score,
                    probabilities=cal,
                    confidence=cal[top] if a.kind == "choice" else a.confidence,
                    calibrated=True,
                )
            )
            any_cal = True
        else:
            out.append(a)
    decision.answers = out
    decision.calibrated = any_cal
    return decision


def default_path() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", Path.home() / ".ownex"))
    return base / "laya_temperatures.json"


def save_temperatures(temperatures: dict[str, float], path: Path | None = None) -> Path:
    p = path or default_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(temperatures, indent=2), encoding="utf-8")
    return p


def load_temperatures(path: Path | None = None) -> dict[str, float]:
    p = path or default_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return {str(k): float(v) for k, v in data.items() if isinstance(v, (int, float))}
    except Exception:
        return {}
