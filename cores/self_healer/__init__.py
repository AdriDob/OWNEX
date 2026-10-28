"""Self-Healer — Auto-repair infrastructure for OWNEX.

Detects anomalies, diagnoses root causes, generates patches,
deploys safely with rollback, and learns from outcomes.
"""

from __future__ import annotations

from cores.self_healer.deployer import SafeDeployer, get_safe_deployer
from cores.self_healer.detector import ProblemDetector, get_problem_detector
from cores.self_healer.learner import SolutionLearner, get_solution_learner
from cores.self_healer.models import (
    Deployment,
    DeploymentStatus,
    Diagnosis,
    FixPlan,
    HealerConfig,
    Patch,
    Problem,
    ProblemSeverity,
)
from cores.self_healer.patcher import PatchGenerator, get_patch_generator
from cores.self_healer.reasoner import RootCauseAnalyzer, get_root_cause_analyzer
from cores.self_healer.scheduler import SelfHealerScheduler, get_self_healer_scheduler

__all__ = [
    "Problem",
    "ProblemSeverity",
    "Diagnosis",
    "FixPlan",
    "Patch",
    "Deployment",
    "DeploymentStatus",
    "HealerConfig",
    "ProblemDetector",
    "get_problem_detector",
    "RootCauseAnalyzer",
    "get_root_cause_analyzer",
    "PatchGenerator",
    "get_patch_generator",
    "SafeDeployer",
    "get_safe_deployer",
    "SolutionLearner",
    "get_solution_learner",
    "SelfHealerScheduler",
    "get_self_healer_scheduler",
]
