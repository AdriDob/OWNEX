"""Tests for BountyPipeline E2E integration."""

import pytest

from core.autonomy.bounty_pipeline import (
    BountyPipeline,
    BountyPipelineConfig,
    BountyPipelineResult,
    get_bounty_pipeline,
)


@pytest.fixture
def pipeline_config():
    """Create test configuration for bounty pipeline."""
    return BountyPipelineConfig(
        algora_token="test_token",
        github_token="test_github_token",
        auto_claim=False,  # Don't actually claim in tests
        auto_submit=False,
        cleanup_repo=True,
        min_test_pass_rate=0.5,  # Lower threshold for tests
        min_confidence_for_pr=0.4,
    )


@pytest.fixture
def bounty_pipeline(pipeline_config):
    """Create bounty pipeline instance."""
    return BountyPipeline(pipeline_config)


def test_bounty_pipeline_initialization(bounty_pipeline):
    """Test bounty pipeline initialization."""
    assert bounty_pipeline is not None
    assert bounty_pipeline.config is not None
    assert bounty_pipeline.repo_analyzer is not None
    assert bounty_pipeline.issue_analyzer is not None
    assert bounty_pipeline.code_generator is not None
    assert bounty_pipeline.test_runner is not None
    assert bounty_pipeline.pr_builder is not None
    assert bounty_pipeline.algora_executor is not None


def test_bounty_pipeline_singleton():
    """Test that get_bounty_pipeline returns the same instance."""
    pipeline1 = get_bounty_pipeline()
    pipeline2 = get_bounty_pipeline()
    assert pipeline1 is pipeline2


def test_bounty_pipeline_config_defaults():
    """Test bounty pipeline configuration defaults."""
    config = BountyPipelineConfig()
    assert config.clone_timeout == 120
    assert config.analysis_timeout == 60
    assert config.generation_timeout == 120
    assert config.test_timeout == 300
    assert config.min_test_pass_rate == 0.8
    assert config.min_confidence_for_pr == 0.6
    assert config.max_iterations == 3
    assert config.auto_claim is True
    assert config.auto_submit is False


def test_bounty_pipeline_result_structure():
    """Test bounty pipeline result structure."""
    result = BountyPipelineResult(
        success=False,
        bounty_id="test-123",
        platform="algora",
    )
    assert result.bounty_id == "test-123"
    assert result.platform == "algora"
    assert result.success is False
    assert result.verdict == ""
    assert result.total_duration_seconds == 0.0
    assert result.phases == {}


@pytest.mark.asyncio
async def test_bounty_pipeline_mock_execution(bounty_pipeline):
    """Test bounty pipeline with mocked execution (no real API calls)."""
    # This would require mocking the analyzer components
    # For now, just test the structure exists
    assert bounty_pipeline.config is not None


def test_bounty_pipeline_config_custom():
    """Test bounty pipeline with custom configuration."""
    config = BountyPipelineConfig(
        clone_timeout=180,
        analysis_timeout=90,
        auto_claim=False,
        auto_submit=True,
    )
    assert config.clone_timeout == 180
    assert config.analysis_timeout == 90
    assert config.auto_claim is False
    assert config.auto_submit is True
