"""
Opportunity Intelligence Layer — read-only public opportunity discovery and prioritization.

Never modifies pipeline data. All outputs are metadata and recommendations.
Supports advanced layered scoring, EVH, and identity vault integration.
"""

from cores.opportunity.engine import OpportunityEngine, get_engine
from cores.opportunity.history import HistoryManager, get_history_manager
from cores.opportunity.models import (
    EVHCalculation,
    EVHRating,
    IdentityVaultEntry,
    Opportunity,
    OpportunityCategory,
    OpportunityProviderInfo,
    OpportunityRecommendations,
    OpportunityScore,
    OpportunitySnapshot,
    OpportunitySource,
    ScoreBreakdown,
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

# Backward-compatible alias
score_opportunity = compute_layered_score

__all__ = [
    "Opportunity", "OpportunitySource", "OpportunityCategory",
    "OpportunityScore", "ScoreBreakdown", "OpportunitySnapshot",
    "OpportunityProviderInfo", "OpportunityRecommendations",
    "EVHCalculation", "EVHRating", "IdentityVaultEntry",
    "OpportunityEngine", "get_engine",
    "BaseProvider", "get_providers",
    "ManualProvider", "PublicProgramProvider",
    "GitHubAdvisoryProvider", "HuntrProvider", "AllSourcesProvider",
    "score_opportunity", "compute_layered_score", "compute_evh", "_score_to_priority",
    "generate_recommendations",
    "HistoryManager", "get_history_manager",
]
