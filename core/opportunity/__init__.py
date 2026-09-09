from __future__ import annotations

# Opportunity Engine - Clean, simple entry point for opportunity intelligence
# This module provides the primary interface for opportunity discovery, scoring, and execution
# New Opportunity Intelligence Engine (multi-type, preparator, scorer)
# Orchestrator for Forge/Pulse cycles (adapters + executors + autonomous agents)
from cores.opportunity.engine import (
    DecisionMode,
    Opportunity,
    OpportunityEngine,
    OpportunityMetrics,
    OpportunityOrchestrator,
    OpportunityPreparator,
    OpportunityScorer,
    OpportunityType,
    PreparationStatus,
    get_engine,
)

# Executors
from cores.opportunity.executors import BaseExecutor, ExecutionResult, get_executors
from cores.opportunity.executors.algora_executor import AlgoraExecutor
from cores.opportunity.executors.freelancer_executor import FreelancerExecutor
from cores.opportunity.executors.issuehunt_executor import IssueHuntExecutor
from cores.opportunity.executors.mindrift_executor import MindriftExecutor
from cores.opportunity.executors.opire_executor import OpireExecutor

# Mercenary filter
from cores.opportunity.mercenary_filter import MercenaryAttributes, get_mercenary_filter

# Scoring models (for tests) - from core/opportunity/models.py
from cores.opportunity.models import (
    OWNEX_WORK_CYCLE_ORDER,
    OWNEX_WORK_CYCLES,
    PersonalHistory,
    ScoredOpportunity,
    Top5Recommendation,
    UnifiedScore,  # This is the test model from models.py
)
from cores.opportunity.personal import PersonalHistoryTracker
from cores.opportunity.scorer import score_opportunity

# Legacy Finding-based scoring engine (backward compatibility)
from cores.opportunity.scoring import (
    OpportunityEngineLegacy,
    get_legacy_engine,
)
from cores.opportunity.scoring import (
    PersonalHistoryTracker as LegacyPersonalHistoryTracker,
)
from cores.opportunity.scoring import (
    Top5Engine as LegacyTop5Engine,
)
from cores.opportunity.scoring import (
    Top5Entry as LegacyTop5Entry,
)
from cores.opportunity.scoring import (
    UnifiedScore as LegacyUnifiedScore,
)

# Top5Engine and PersonalHistoryTracker for tests (from cores/opportunity)
from cores.opportunity.top5 import Top5Engine

# Export all
__all__ = [
    # New Opportunity Intelligence Engine
    "OpportunityEngine",
    "Opportunity",
    "OpportunityType",
    "OpportunityMetrics",
    "PreparationStatus",
    "DecisionMode",
    "OpportunityScorer",
    "OpportunityPreparator",
    "get_engine",
    # Legacy (backward compat) - prefixed to avoid conflicts
    "OpportunityEngineLegacy",
    "LegacyUnifiedScore",
    "LegacyTop5Entry",
    "LegacyTop5Engine",
    "LegacyPersonalHistoryTracker",
    "get_legacy_engine",
    # Scoring models (for tests) - from core/opportunity/models.py
    "OWNEX_WORK_CYCLES",
    "OWNEX_WORK_CYCLE_ORDER",
    "PersonalHistory",
    "ScoredOpportunity",
    "Top5Recommendation",
    "UnifiedScore",  # test model
    "score_opportunity",
    # Top5Engine and PersonalHistoryTracker for tests (from cores/opportunity)
    "Top5Engine",
    "PersonalHistoryTracker",
    # Orchestrator
    "OpportunityOrchestrator",
    # Executors
    "BaseExecutor",
    "ExecutionResult",
    "get_executors",
    "FreelancerExecutor",
    "AlgoraExecutor",
    "MindriftExecutor",
    "OpireExecutor",
    "IssueHuntExecutor",
    # Mercenary
    "MercenaryAttributes",
    "get_mercenary_filter",
]
