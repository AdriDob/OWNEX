"""
Universal Opportunity Discovery Engine

Continuously explores the internet for new platforms, programs, rewards,
contests, and public paid opportunities compatible with OWNEX philosophy.
"""

from __future__ import annotations

__version__ = "1.0.0"

from .analyzer import AnalysisResult, PlatformAnalyzer
from .classifier import ClassificationResult, PlatformClassifier
from .deduplicator import Deduplicator, DuplicateResult
from .discovery import DiscoveryConfig, DiscoveryEngine
from .knowledge import KnowledgeBase, PlatformRecord
from .scheduler import ContinuousScheduler, SchedulerConfig
from .scorer import OwnExScorer, ScoreResult

__all__ = [
    "DiscoveryEngine",
    "DiscoveryConfig",
    "PlatformClassifier",
    "ClassificationResult",
    "Deduplicator",
    "DuplicateResult",
    "PlatformAnalyzer",
    "AnalysisResult",
    "OwnExScorer",
    "ScoreResult",
    "KnowledgeBase",
    "PlatformRecord",
    "ContinuousScheduler",
    "SchedulerConfig",
]
