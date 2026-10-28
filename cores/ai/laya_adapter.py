"""LAYA decision adapter — structured decisions, NOT chat.

LAYA (convaiinnovations/laya, 421M, Apache-2.0) is a non-autoregressive
decision encoder. It answers typed questions (choice / score / noul) with
calibrated probabilities. It never generates text.

This adapter is deliberately NOT an AIProviderProtocol / chat provider:
it cannot hold a conversation, write code, or explain. It emits one
LayaDecision per call: labels + probabilities + confidence.

Honesty rules:
- torch/transformers/weights missing → UNAVAILABLE with reason, never FAIL.
- Nothing is auto-downloaded. Weights must be provisioned explicitly.
- choice with >MAX_OPTIONS options is rejected (upstream degrades past ~20).
- Raw probabilities are UNCALIBRATED until passed through
  cores.ai.laya_calibration with temperatures fit on OWN data.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("ownex.ai.laya")

LAYA_MODEL_DEFAULT = "convaiinnovations/laya"
LAYA_MODEL_TYPED_DECISIONS = "convaiinnovations/laya-typed-decisions"

# Upstream evidence: >20 options per question collapses accuracy.
MAX_OPTIONS = 20
MIN_OPTIONS = 2


class LayaUnavailableError(Exception):
    """Raised when LAYA cannot run. Callers must fall back to UNKNOWN."""


# Backwards-compatible alias (short name used by callers/tests).
LayaUnavailable = LayaUnavailableError


@dataclass(slots=True)
class LayaQuestion:
    """One typed question over a state string."""

    name: str
    kind: str  # "choice" | "score" | "noul"
    options: list[str] = field(default_factory=list)  # choice only
    levels: int = 5  # score only (ordinal 1..levels)


@dataclass(slots=True)
class LayaAnswer:
    """One answered question."""

    name: str
    kind: str
    label: str | None = None  # choice top label
    probability: float | None = None  # noul P(true) or choice top prob
    score: float | None = None  # score expected level
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    calibrated: bool = False


@dataclass(slots=True)
class LayaDecision:
    """Full decision: every question answered in one forward pass."""

    answers: list[LayaAnswer]
    model: str
    latency_ms: float
    calibrated: bool = False

    def by_name(self, name: str) -> LayaAnswer | None:
        for a in self.answers:
            if a.name == name:
                return a
        return None


# Backend protocol: (state, questions_payload) -> raw answer dicts.
# The real backend wraps laya.load(); tests inject a fake.
BackendFn = Callable[[str, list[dict[str, Any]]], list[dict[str, Any]]]


def _real_backend(state: str, payload: list[dict[str, Any]], model: str) -> list[dict[str, Any]]:
    """Run the real LAYA model. Import-lazy so the module stays import-safe."""
    try:
        import laya  # type: ignore[import-not-found]
    except Exception as exc:
        raise LayaUnavailable(f"laya package not installed: {exc}") from exc
    try:
        agent = laya.load(model)
    except Exception as exc:
        raise LayaUnavailable(f"cannot load LAYA weights ({model}): {exc}") from exc
    try:
        result = agent.decide(state=state, questions=payload)
    except Exception as exc:
        raise LayaUnavailable(f"LAYA inference failed: {exc}") from exc
    answers = result.get("answers") if isinstance(result, dict) else getattr(result, "answers", None)
    if not isinstance(answers, list):
        raise LayaUnavailable("LAYA returned no answers")
    return [dict(a) if isinstance(a, dict) else {"label": str(a)} for a in answers]


def finding_questions(finding: dict[str, Any]) -> list[LayaQuestion]:
    """Build the pilot question set for a finding candidate (pure, no model).

    Pilot C: confidence gate. Two bounded questions, never a verdict:
    - severity_signal (choice, 5 options ≤ MAX_OPTIONS)
    - credibility (noul: true-positive given the evidence)
    """
    return [
        LayaQuestion(
            name="severity_signal",
            kind="choice",
            options=["critical", "high", "medium", "low", "informative"],
        ),
        LayaQuestion(name="credibility", kind="noul"),
    ]


def finding_state(finding: dict[str, Any]) -> str:
    """Compact state text for a finding candidate (pure, truncated)."""
    parts = [
        str(finding.get("vuln_type") or finding.get("type") or "unknown"),
        str(finding.get("endpoint") or finding.get("url") or ""),
        str(finding.get("evidence_summary") or finding.get("evidence") or "")[:500],
    ]
    return " | ".join(p for p in parts if p)[:800]


class LayaAdapter:
    """Isolated LAYA decision engine. Opt-in, lazy, honest."""

    def __init__(
        self,
        model: str | None = None,
        backend: BackendFn | None = None,
    ) -> None:
        self._model = model or os.environ.get("LAYA_MODEL", LAYA_MODEL_DEFAULT)
        self._backend = backend
        self._unavailable_reason: str | None = None

    @property
    def model(self) -> str:
        return self._model

    def check(self) -> bool:
        """True only if a decision could run right now. Never raises."""
        if os.environ.get("LAYA_DISABLED", "").strip() == "1":
            self._unavailable_reason = "disabled by LAYA_DISABLED=1"
            return False
        if self._backend is not None:
            self._unavailable_reason = None
            return True
        try:
            import laya  # type: ignore[import-not-found]  # noqa: F401
        except Exception as exc:
            self._unavailable_reason = f"laya not installed ({exc})"
            return False
        self._unavailable_reason = None
        return True

    def status(self) -> dict[str, Any]:
        ok = self.check()
        return {
            "available": ok,
            "model": self._model,
            "reason": None if ok else self._unavailable_reason,
            "capabilities": ["choice", "score", "noul"],
            "chat": False,
        }

    @staticmethod
    def _validate(questions: list[LayaQuestion]) -> None:
        if not questions:
            raise ValueError("no questions")
        for q in questions:
            if q.kind == "choice":
                n = len(q.options)
                if n < MIN_OPTIONS:
                    raise ValueError(f"question {q.name}: need ≥{MIN_OPTIONS} options")
                if n > MAX_OPTIONS:
                    raise ValueError(f"question {q.name}: {n} options exceed MAX_OPTIONS={MAX_OPTIONS}")
            elif q.kind == "score":
                if q.levels < 2:
                    raise ValueError(f"question {q.name}: levels must be ≥2")
            elif q.kind == "noul":
                continue
            else:
                raise ValueError(f"question {q.name}: unknown kind {q.kind!r}")

    def decide(self, state: str, questions: list[LayaQuestion]) -> LayaDecision:
        """Answer typed questions over state. Fail-closed on misuse/unavailable."""
        if not state or not state.strip():
            raise ValueError("empty state")
        self._validate(questions)
        if not self.check():
            raise LayaUnavailable(self._unavailable_reason or "unavailable")
        payload = [
            {
                "name": q.name,
                "kind": q.kind,
                "options": list(q.options),
                "levels": q.levels,
            }
            for q in questions
        ]
        t0 = time.monotonic()
        raw = self._backend(state, payload) if self._backend is not None else _real_backend(state, payload, self._model)
        dur = (time.monotonic() - t0) * 1000
        answers = []
        for q, r in zip(questions, raw, strict=False):
            answers.append(
                LayaAnswer(
                    name=q.name,
                    kind=q.kind,
                    label=r.get("label"),
                    probability=r.get("probability"),
                    score=r.get("score"),
                    probabilities=dict(r.get("probabilities") or {}),
                    confidence=float(r.get("confidence") or 0.0),
                    calibrated=False,
                )
            )
        return LayaDecision(answers=answers, model=self._model, latency_ms=round(dur, 1))
