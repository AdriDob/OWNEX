"""Senior Copilot Agent — transversal reasoning, quality, and control center for ORION.

The Copilot consumes Core Services (EventBus, Decision Journal, Memory, System State)
through their public interfaces. It never accesses apps directly.
"""

from __future__ import annotations

from core.copilot.agent import CopilotAgent
from core.copilot.analyzer import AnalysisResult, FindingAnalyzer
from core.copilot.auditor import (
    ArchitectureAuditor,
    AuditFinding,
    AuditReport,
    ConfigurationAuditor,
    HealthAuditor,
    IAuditor,
    SecurityAuditor,
)
from core.copilot.config import CopilotConfig
from core.copilot.context import CopilotContext
from core.copilot.explain import ExplanationEngine
from core.copilot.permissions import AuthorityLevel, DecisionConfidence, Policy, PolicyEngine
from core.copilot.planner import Plan, Planner, PlanStep
from core.copilot.recommender import Recommendation, Recommender
from core.copilot.review import CopilotReview, ReviewItem, ReviewReport
from core.copilot.system_context import SystemContextBuilder

__all__ = [
    "CopilotAgent",
    "CopilotConfig",
    "CopilotContext",
    "AuthorityLevel",
    "DecisionConfidence",
    "Policy",
    "PolicyEngine",
    "ExplanationEngine",
    "AnalysisResult",
    "FindingAnalyzer",
    "Plan",
    "PlanStep",
    "Planner",
    "Recommendation",
    "Recommender",
    "CopilotReview",
    "SystemContextBuilder",
    "ReviewItem",
    "ReviewReport",
    "IAuditor",
    "AuditFinding",
    "AuditReport",
    "HealthAuditor",
    "ConfigurationAuditor",
    "SecurityAuditor",
    "ArchitectureAuditor",
]
