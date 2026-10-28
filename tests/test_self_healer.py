"""Self-healer unit tests.

Covers:
- cores.self_healer.models
- cores.self_healer.detector
- cores.self_healer.reasoner
- cores.self_healer.learner
"""

import os
import sys

# Ensure the project root is on the path so `cores.*` imports work
sys.path.insert(0, os.path.dirname(__file__))

from cores.self_healer.detector import DEFAULT_THRESHOLDS, ProblemDetector
from cores.self_healer.learner import LEARNING_NAMESPACE, SolutionLearner
from cores.self_healer.models import (
    Deployment,
    Diagnosis,
    FixPlan,
    HealerConfig,
    Patch,
    Problem,
)
from cores.self_healer.reasoner import KNOWN_PATTERNS, RootCauseAnalyzer


def test_models_basic():
    """Instantiate all model dataclasses and check default values."""
    p = Problem(name="test", severity=5, category="test_cat")
    assert p.name == "test"
    assert p.severity == 5
    assert p.category == "test_cat"

    d = Diagnosis(name="test_diag", confidence=0.9, evidence=["ev1"])
    assert d.name == "test_diag"
    assert d.confidence == 0.9
    assert "ev1" in d.evidence

    fp = FixPlan(
        title="test_fix",
        description="desc",
        estimated_effort="1h",
        risk="low",
        steps=["step1"],
    )
    assert fp.title == "test_fix"
    assert fp.estimated_effort == "1h"
    assert fp.risk == "low"
    assert fp.steps == ["step1"]

    patch = Patch(
        title="test_patch",
        description="desc",
        changes=["change1"],
        rollback_steps=["rollback1"],
    )
    assert patch.title == "test_patch"
    assert patch.changes == ["change1"]
    assert patch.rollback_steps == ["rollback1"]

    dep = Deployment(
        name="test_deploy",
        target="prod",
        command="deploy.sh",
        timeout=300,
    )
    assert dep.name == "test_deploy"
    assert dep.target == "prod"
    assert dep.command == "deploy.sh"
    assert dep.timeout == 300

    cfg = HealerConfig(
        enabled=True,
        max_retries=3,
        cooldown=60,
        dry_run=False,
    )
    assert cfg.enabled is True
    assert cfg.max_retries == 3
    assert cfg.cooldown == 60
    assert cfg.dry_run is False


def test_detector_basic():
    """ProblemDetector basic instantiation and threshold checks."""
    detector = ProblemDetector()
    assert detector is not None

    # DEFAULT_THRESHOLDS should be a dict-like object
    thresholds = DEFAULT_THRESHOLDS
    assert thresholds is not None
    # Typical keys; adjust if the dict structure differs
    assert isinstance(thresholds, dict)


def test_reasoner_basic():
    """RootCauseAnalyzer and KNOWN_PATTERNS basic checks."""
    analyzer = RootCauseAnalyzer()
    assert analyzer is not None

    patterns = KNOWN_PATTERNS
    assert patterns is not None
    assert isinstance(patterns, dict)


def test_learner_basic():
    """SolutionLearner basic instantiation and namespace."""
    learner = SolutionLearner()
    assert learner is not None

    ns = LEARNING_NAMESPACE
    assert ns == "self_healer"


if __name__ == "__main__":
    # Allow running directly for quick feedback
    pytest.main([__file__, "-v"])
