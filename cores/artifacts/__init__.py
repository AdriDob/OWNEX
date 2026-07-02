"""
core.artifacts — Canonical artifact objects for the system.

One Concept = One Canonical Object.
Every engine produces exactly one artifact type.
All consumers read from artifacts only.
"""

from cores.artifacts.ai_insights import (
    AIInsightArtifact,
)
from cores.artifacts.attack_surface import (
    AttackSurfaceArtifact,
)
from cores.artifacts.differential import (
    DifferentialArtifact,
)
from cores.artifacts.evidence import (
    EvidenceGraphArtifact,
)
from cores.artifacts.execution import (
    ExecutionPlanArtifact,
)
from cores.artifacts.hypothesis import (
    HypothesisArtifact,
)
from cores.artifacts.pipeline import (
    PipelineArtifact,
)
from cores.artifacts.quick_wins import (
    QuickWinsArtifact,
)
from cores.artifacts.roi import (
    ROIArtifact,
)
from cores.artifacts.screenshot import (
    ScreenshotArtifact,
)

__all__ = [
    "PipelineArtifact",
    "EvidenceGraphArtifact",
    "ScreenshotArtifact",
    "DifferentialArtifact",
    "QuickWinsArtifact",
    "ExecutionPlanArtifact",
    "AIInsightArtifact",
    "AttackSurfaceArtifact",
    "ROIArtifact",
    "HypothesisArtifact",
]
