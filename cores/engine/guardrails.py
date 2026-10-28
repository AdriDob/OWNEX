"""
guardrails — Architectural enforcement for CATEYE's single-source-of-truth.

ONLY_PIPELINE_CAN_SCORE = True

This module provides runtime enforcement hooks and documentation
to ensure no component computes its own risk_score outside of
cores/engine/unified_scoring.py.
"""

ONLY_PIPELINE_CAN_SCORE = True

SOURCE_OF_TRUTH = "cores.engine.unified_scoring.score"

AUTHORIZED_SCORING_CONSUMERS = {
    "cores.engine.unified_scoring",
    "cores.engine.unified_classifier",
    "cores.engine.priority_rebalancer",
    "cores.engine.risk_model",
}

FORBIDDEN_IMPORTS: set[str] = {
    "cores.targets.scorer",
}


class ScoringViolationError(RuntimeError):
    """
    Raised when legacy scoring is invoked at runtime.
    Only active when ONLY_PIPELINE_CAN_SCORE is True.
    """


def assert_no_legacy_scoring():
    """
    Runtime guard: ensures legacy scoring modules are not importable.
    Call at startup to fail fast if old code paths remain.
    """
    for mod in FORBIDDEN_IMPORTS:
        if mod in __import__("sys").modules:
            raise ScoringViolationError(f"Legacy scoring module loaded: {mod}. Use {SOURCE_OF_TRUTH} instead.")
