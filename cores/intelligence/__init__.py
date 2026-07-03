"""
Core intelligence modules for CATEYE.

Sub-packages:
  Unification layer: dependency_graph, event_system, cache, anti_drift
  Learning layer: adaptive_memory, pattern_registry, historical_analyzer,
                  trend_detector, recommendation_engine, learning_snapshot
"""

from cores.intelligence.adaptive_memory import AdaptiveMemory, get_memory, reset_memory
from cores.intelligence.anti_drift import AntiDriftEnforcer
from cores.intelligence.cache import ArtifactCache
from cores.intelligence.dependency_graph import DependencyGraph
from cores.intelligence.event_system import EventSystem
from cores.intelligence.historical_analyzer import HistoricalSummary, analyze_historical_data
from cores.intelligence.learning_snapshot import LearningSnapshot, generate_snapshot
from cores.intelligence.pattern_registry import PatternRegistry, PatternStats, get_registry, reset_registry
from cores.intelligence.recommendation_engine import RecommendationBundle, generate_recommendations
from cores.intelligence.reward_learning import (
    ProgramRewardMetrics,
    RewardLearner,
    RewardLearningReport,
    VulnTypeStats,
)
from cores.intelligence.trend_detector import TrendReport, TrendSignal, detect_trends
from cores.intelligence.unified_orchestrator import UnifiedOrchestrator, get_orchestrator

__all__ = [
    "DependencyGraph", "EventSystem", "ArtifactCache", "AntiDriftEnforcer",
    "UnifiedOrchestrator", "get_orchestrator",
    "AdaptiveMemory", "get_memory", "reset_memory",
    "PatternRegistry", "PatternStats", "get_registry", "reset_registry",
    "HistoricalSummary", "analyze_historical_data",
    "TrendReport", "TrendSignal", "detect_trends",
    "RecommendationBundle", "generate_recommendations",
    "LearningSnapshot", "generate_snapshot",
    "RewardLearner", "RewardLearningReport", "ProgramRewardMetrics", "VulnTypeStats",
]
