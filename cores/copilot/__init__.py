"""Senior Copilot Agent — transversal reasoning, quality, and control center for ORION.

The Copilot consumes Core Services (EventBus, Decision Journal, Memory, System State)
through their public interfaces. It never accesses apps directly.
"""

from __future__ import annotations

from cores.copilot.agent import CopilotAgent
from cores.copilot.analyzer import AnalysisResult, FindingAnalyzer
from cores.copilot.auditor import (
    ArchitectureAuditor,
    AuditFinding,
    AuditReport,
    ConfigurationAuditor,
    HealthAuditor,
    IAuditor,
    SecurityAuditor,
)
from cores.copilot.config import CopilotConfig
from cores.copilot.context import CopilotContext
from cores.copilot.explain import ExplanationEngine
from cores.copilot.permissions import AuthorityLevel, DecisionConfidence, Policy, PolicyEngine
from cores.copilot.planner import Plan, Planner, PlanStep
from cores.copilot.recommender import Recommendation, Recommender
from cores.copilot.review import CopilotReview, ReviewItem, ReviewReport
from cores.copilot.system_context import SystemContextBuilder

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
