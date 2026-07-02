"""
Core modules for Rastro.

Sub-packages:
  contracts/  — Canonical interfaces and base classes
  artifacts/  — Canonical artifact bundles (system-wide data objects)
  intelligence/ — Unification layer (dependency graph, events, cache, anti-drift)
  ... (existing engines remain unchanged)
"""

from cores.artifacts import (
    AIInsightArtifact,
    AttackSurfaceArtifact,
    DifferentialArtifact,
    EvidenceGraphArtifact,
    ExecutionPlanArtifact,
    HypothesisArtifact,
    PipelineArtifact,
    QuickWinsArtifact,
    ROIArtifact,
    ScreenshotArtifact,
)
from cores.contracts import Artifact, Bundle
from cores.intelligence import (
    AntiDriftEnforcer,
    ArtifactCache,
    DependencyGraph,
    EventSystem,
    UnifiedOrchestrator,
    get_orchestrator,
)
from cores.opportunity import (
    BaseProvider,
    HistoryManager,
    Opportunity,
    OpportunityCategory,
    OpportunityEngine,
    OpportunityRecommendations,
    OpportunityScore,
    OpportunitySnapshot,
    OpportunitySource,
    generate_recommendations,
    get_engine,
    get_history_manager,
    get_providers,
    score_opportunity,
)
