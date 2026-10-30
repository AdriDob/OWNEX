"""Acceptance Intelligence — learn what gets paid.

Core premise: every submission outcome is a data point.
Over time, the system learns which report characteristics
maximize acceptance probability per platform.

Modules:
    models    — data structures for outcomes and profiles
    analyzer  — pattern detection across historical outcomes
    predictor — acceptance probability estimation
    optimizer — report improvement suggestions based on patterns
"""

from __future__ import annotations

from cores.acceptance.analyzer import AcceptanceAnalyzer
from cores.acceptance.models import AcceptanceOutcome, PlatformProfile, SubmissionRecord
from cores.acceptance.optimizer import AcceptanceOptimizer
from cores.acceptance.predictor import AcceptancePredictor

__all__ = [
    "AcceptanceAnalyzer",
    "AcceptanceOutcome",
    "AcceptanceOptimizer",
    "AcceptancePredictor",
    "PlatformProfile",
    "SubmissionRecord",
]
