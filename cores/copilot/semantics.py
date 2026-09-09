"""AI response semantics — FACT / INFERENCE / RECOMMENDATION / UNKNOWN.

Every AI-shaped answer in OWNEX must distinguish what the system measured
from what it guessed. This module is the single contract:

- FACT:           measured from runtime state (counts, scores, records).
- INFERENCE:      derived by a model/scorer (estimates, probabilities).
- RECOMMENDATION: suggested next action (always reviewable, never auto-executed).
- UNKNOWN:        explicitly missing data (never filled with invention).

Rendering is deterministic markdown; no LLM needed to label OWNEX's own state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class SemanticResponse:
    """One labeled AI answer."""

    facts: list[str] = field(default_factory=list)
    inferences: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "FACT": list(self.facts),
            "INFERENCE": list(self.inferences),
            "RECOMMENDATION": list(self.recommendations),
            "UNKNOWN": list(self.unknowns),
        }

    def render_markdown(self) -> str:
        lines: list[str] = []
        for label, items in (
            ("FACT", self.facts),
            ("INFERENCE", self.inferences),
            ("RECOMMENDATION", self.recommendations),
            ("UNKNOWN", self.unknowns),
        ):
            if not items:
                continue
            lines.append(f"**{label}:**")
            lines.extend(f"- {item}" for item in items)
        return "\n".join(lines)


def build_daily_brief_semantics(
    *,
    scanned: int,
    top_title: str | None,
    top_score: float | None,
    top_ev_per_hour: float | None,
    missing_skills: list[str] | None = None,
    has_payment_method: bool = False,
) -> SemanticResponse:
    """Label a daily-brief answer from measured inputs (no invention)."""
    facts = [f"Scanned {scanned} opportunities from registered adapters."]
    inferences: list[str] = []
    recommendations: list[str] = []
    unknowns: list[str] = []

    if top_title and top_score is not None:
        facts.append(f"Top pick: {top_title} (score {top_score:.0f}/100).")
        inferences.append("The top pick maximizes expected value per human hour among scanned opportunities.")
        if top_ev_per_hour is not None:
            inferences.append(f"Estimated value: ${top_ev_per_hour:.2f}/human-hour (estimate, not a promise).")
    else:
        unknowns.append("No recommendable opportunity found in this scan.")
    if missing_skills:
        recommendations.append(f"Close the skill gap first: {', '.join(missing_skills[:3])}.")
    if not has_payment_method:
        unknowns.append("Payout path not verified for the top pick: confirm payment method before executing.")
    recommendations.append("Review the top pick, then approve explicitly before any external action.")

    return SemanticResponse(facts=facts, inferences=inferences, recommendations=recommendations, unknowns=unknowns)


# Phrases by which a model explicitly marks its own uncertainty (EN + ES).
# Matched case-insensitively as substrings; deliberately narrow to avoid
# mislabeling confident statements as unknown.
_UNCERTAINTY_MARKERS: tuple[str, ...] = (
    "i don't know",
    "i'm not sure",
    "i am not sure",
    "i cannot verify",
    "i can't verify",
    "unable to verify",
    "unknown",
    "no estoy seguro",
    "no estoy segura",
    "no lo sé",
    "no se puede verificar",
    "no puedo verificarlo",
    "desconozco",
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_UNVERIFIED_MODEL_OUTPUT = (
    "Unverified model output: confirm against /daily-brief, the revenue ledger, or a platform guide before acting."
)


def label_free_text(text: str) -> SemanticResponse:
    """Label free model text with minimal honest semantics.

    Rule: model-generated sentences are INFERENCE by default (never FACT),
    sentences carrying explicit uncertainty markers move to UNKNOWN, and every
    response carries the standing UNKNOWN that model output is unverified.
    Deterministic, no LLM involved.
    """
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text or "") if s.strip()]
    inferences: list[str] = []
    unknowns: list[str] = [_UNVERIFIED_MODEL_OUTPUT]
    for sentence in sentences:
        lowered = sentence.lower()
        if any(marker in lowered for marker in _UNCERTAINTY_MARKERS):
            unknowns.append(sentence)
        else:
            inferences.append(sentence)
    return SemanticResponse(inferences=inferences, unknowns=unknowns)
