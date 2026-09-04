"""Direct Work Engine — universal remote opportunity discovery, analysis, and execution.

Discovers and scores remote technology opportunities across every supported
category. The Zero Barrier Score ranks how *low* the entry barrier is on a
continuous 0-100 spectrum — it never promises that zero barrier exists
everywhere, only finds the opportunities closest to it.
"""

from __future__ import annotations

from cores.direct_work_engine.availability import (
    AvailabilityEngine,
    AvailabilitySnapshot,
    TimeBlock,
    can_accommodate_task,
    get_availability_engine,
    get_availability_snapshot,
    get_available_hours,
    recommend_max_task_hours,
)
from cores.direct_work_engine.evaluation import DirectWorkEvaluationEngine, EvaluationResult, evaluate_work_item
from cores.direct_work_engine.engine import DirectWorkEngine, EngineStats, get_direct_work_engine
from cores.direct_work_engine.evolution import (
    CapabilityExpansionDetector,
    CapabilityProposal,
    LostOpportunityLesson,
    PerformanceAnalysis,
    PerformanceAnalyzer,
    SkillEvolutionEngine,
    evolve_analysis,
)
from cores.direct_work_engine.execution import DirectWorkExecutionEngine, ExecutionResult, execute_work_item
from cores.direct_work_engine.delivery import DirectWorkDeliveryEngine, DeliveryResult, deliver_work_item
from cores.direct_work_engine.evolution import (
    CapabilityExpansionDetector,
    CapabilityProposal,
    LostOpportunityLesson,
    PerformanceAnalysis,
    PerformanceAnalyzer,
    SkillEvolutionEngine,
    evolve_analysis,
)
from cores.direct_work_engine.extension import ExtensionEvaluator, ExtensionProposal
from cores.direct_work_engine.feedback import LearningRecord, apply_learning, build_history_from_revenue_tracker
from cores.direct_work_engine.learning import DirectWorkLearningEngine, LearningResult, learn_from_outcome
from cores.direct_work_engine.models import (
    INTERNATIONAL_PAYMENT_METHODS,
    PAYMENT_RELIABILITY,
    BarrierLevel,
    DifficultyLevel,
    EmploymentType,
    ExperienceLevel,
    GameDevSpecialization,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    RankedOpportunity,
    UserProfile,
    WorkPlatform,
    ZeroBarrierScore,
)
from cores.direct_work_engine.negotiation import TermAnalyzer, TermAssessment
from cores.direct_work_engine.profile_builder import IntelligentProfileBuilder, ProfileAssets
from cores.direct_work_engine.recommendation import (
    DEFAULT_RECOMMENDER_CONFIG,
    FAST_INCOME_RECOMMENDER_CONFIG,
    MAX_SUCCESS_RECOMMENDER_CONFIG,
    IntelligentRecommender,
    RecommenderConfig,
)
from cores.direct_work_engine.scoring import ZeroBarrierScorer, score_opportunities
from cores.direct_work_engine.skill_gap import SkillAmplifier, SkillGapReport
from cores.direct_work_engine.workbank import WorkBank, WorkItem, get_workbank

__all__ = [
    "AvailabilityEngine",
    "AvailabilitySnapshot",
    "BarrierLevel",
    "CapabilityExpansionDetector",
    "CapabilityProposal",
    "DEFAULT_RECOMMENDER_CONFIG",
    "DifficultyLevel",
    "DirectWorkEngine",
    "DirectWorkEvaluationEngine",
    "DirectWorkExecutionEngine",
    "DirectWorkDeliveryEngine",
    "DirectWorkLearningEngine",
    "EmploymentType",
    "EngineStats",
    "EvaluationResult",
    "ExperienceLevel",
    "EvaluationResult",
    "ExtensionEvaluator",
    "ExtensionProposal",
    "FAST_INCOME_RECOMMENDER_CONFIG",
    "GameDevSpecialization",
    "INTERNATIONAL_PAYMENT_METHODS",
    "IntelligentProfileBuilder",
    "IntelligentRecommender",
    "LearningRecord",
    "LearningResult",
    "LostOpportunityLesson",
    "MAX_SUCCESS_RECOMMENDER_CONFIG",
    "Opportunity",
    "OpportunityCategory",
    "PAYMENT_RELIABILITY",
    "PaymentMethod",
    "PerformanceAnalysis",
    "PerformanceAnalyzer",
    "ProfileAssets",
    "RankedOpportunity",
    "RecommenderConfig",
    "SkillAmplifier",
    "SkillEvolutionEngine",
    "SkillGapReport",
    "TermAnalyzer",
    "TermAssessment",
    "TimeBlock",
    "UserProfile",
    "WorkBank",
    "WorkItem",
    "WorkPlatform",
    "ZeroBarrierScore",
    "ZeroBarrierScorer",
    "apply_learning",
    "build_history_from_revenue_tracker",
    "can_accommodate_task",
    "evaluate_work_item",
    "evolve_analysis",
    "execute_work_item",
    "get_available_hours",
    "get_availability_engine",
    "get_availability_snapshot",
    "get_direct_work_engine",
    "get_workbank",
    "learn_from_outcome",
    "recommend_max_task_hours",
    "score_opportunities",
]
