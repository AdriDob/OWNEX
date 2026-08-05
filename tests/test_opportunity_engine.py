import pytest

from core.opportunity.scoring import OpportunityEngineLegacy, UnifiedScore


@pytest.fixture
def engine():
    return OpportunityEngineLegacy()


@pytest.fixture
def sample_candidates():
    return [
        UnifiedScore(
            opportunity_id=1,
            target_id=1,
            program_id=1,
            title="Critical SSRF",
            severity="critical",
            reward=5000,
            difficulty=0.3,
            acceptance_prob=0.8,
            evh=10000,
            personal_factor=1.0,
        ),
        UnifiedScore(
            opportunity_id=2,
            target_id=2,
            program_id=2,
            title="High JWT Token Leak",
            severity="high",
            reward=2000,
            difficulty=0.5,
            acceptance_prob=0.6,
            evh=2400,
            personal_factor=1.0,
        ),
        UnifiedScore(
            opportunity_id=3,
            target_id=3,
            program_id=3,
            title="Medium XSS",
            severity="medium",
            reward=1000,
            difficulty=0.7,
            acceptance_prob=0.4,
            evh=571,
            personal_factor=1.2,
        ),
        UnifiedScore(
            opportunity_id=4,
            target_id=4,
            program_id=4,
            title="Low Misconfiguration",
            severity="low",
            reward=500,
            difficulty=0.9,
            acceptance_prob=0.3,
            evh=75,
            personal_factor=0.8,
        ),
    ]


def test_unified_score_calculation():
    UnifiedScore(
        opportunity_id=1,
        target_id=1,
        program_id=1,
        title="Test",
        severity="high",
        reward=1000,
        difficulty=0.4,
        acceptance_prob=0.7,
        evh=1700,
    )


@pytest.fixture
def personal_tracker_fixture(engine):
    tracker = engine.tracker
    return tracker
