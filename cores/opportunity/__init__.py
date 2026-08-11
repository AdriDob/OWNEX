"""
Opportunity Intelligence Layer — read-only public opportunity discovery and prioritization.

Never modifies pipeline data. All outputs are metadata and recommendations.
Supports advanced layered scoring, EVH, and identity vault integration.
"""

# Legacy compatibility layer for tests (from core.opportunity.models)
from core.opportunity.models import (
    OWNEX_WORK_CYCLE_ORDER,
    OWNEX_WORK_CYCLES,
    PersonalHistory,
    PersonalHistoryTracker,
    ScoredOpportunity,
    Top5Engine,
    Top5Recommendation,
    UnifiedScore,
    score_opportunity,
)
from cores.opportunity.engine import (
    Opportunity,
    OpportunityCategory,
    OpportunityEngine,
    OpportunityFilter,
    OpportunityRanker,
    OpportunitySource,
    RankedOpportunity,
    get_engine,
    get_opportunity_engine,
)
from cores.opportunity.history import HistoryManager, get_history_manager
from cores.opportunity.models import (
    EVHCalculation,
    EVHRating,
    IdentityVaultEntry,
    OpportunityProviderInfo,
    OpportunityRecommendations,
    OpportunityScore,
    OpportunitySnapshot,
    ScoreBreakdown,
)
from cores.opportunity.models import (
    Opportunity as LegacyOpportunity,
)
from cores.opportunity.models import (
    OpportunityCategory as LegacyOpportunityCategory,
)
from cores.opportunity.models import (
    OpportunitySource as LegacyOpportunitySource,
)
from cores.opportunity.providers import (
    AllSourcesProvider,
    BaseProvider,
    GitHubAdvisoryProvider,
    HuntrProvider,
    ManualProvider,
    PublicProgramProvider,
    get_providers,
)
from cores.opportunity.recommendations import generate_recommendations
from cores.opportunity.scoring2 import _score_to_priority, compute_evh, compute_layered_score

__all__ = [
    "OpportunityEngine",
    "get_opportunity_engine",
    "OpportunityCategory",
    "OpportunitySource",
    "Opportunity",
    "RankedOpportunity",
    "OpportunityFilter",
    "OpportunityRanker",
    "EVHCalculation",
    "EVHRating",
    "IdentityVaultEntry",
    "OpportunityRecommendations",
    "BaseProvider",
    "get_providers",
    "ManualProvider",
    "PublicProgramProvider",
    "GitHubAdvisoryProvider",
    "HuntrProvider",
    "AllSourcesProvider",
    "compute_layered_score",
    "compute_evh",
    "_score_to_priority",
    "generate_recommendations",
    "HistoryManager",
    "get_history_manager",
    # Legacy compatibility
    "OWNEX_WORK_CYCLES",
    "OWNEX_WORK_CYCLE_ORDER",
    "PersonalHistory",
    "PersonalHistoryTracker",
    "ScoredOpportunity",
    "Top5Engine",
    "Top5Recommendation",
    "UnifiedScore",
    "score_opportunity",
]
