"""Tests for Dev Bounty Pipeline."""

from __future__ import annotations

from core.autonomy.dev_bounty_pipeline import DevBountyPipeline, DevBountyPipelineConfig, get_dev_bounty_pipeline


def test_dev_bounty_pipeline_initialization():
    """Test pipeline initializes correctly."""
    config = DevBountyPipelineConfig()
    pipeline = DevBountyPipeline(config)
    assert pipeline is not None
    assert pipeline.config == config
    assert hasattr(pipeline, "executors")
    assert "freelancer" in pipeline.executors
    assert "opire" in pipeline.executors
    assert "issuehunt" in pipeline.executors


def test_dev_bounty_pipeline_singleton():
    """Test global instance returns same object."""
    p1 = get_dev_bounty_pipeline()
    p2 = get_dev_bounty_pipeline()
    assert p1 is p2


def test_dev_bounty_pipeline_config_defaults():
    """Test default configuration values."""
    config = DevBountyPipelineConfig()
    assert config.clone_timeout == 120
    assert config.analysis_timeout == 60
    assert config.generation_timeout == 120
    assert config.test_timeout == 300
    assert config.pr_timeout == 60
    assert config.submit_timeout == 30
    assert config.min_test_pass_rate == 0.8
    assert config.min_confidence_for_pr == 0.6
    assert config.max_iterations == 3
    assert config.auto_submit is True  # Changed: auto-submit enabled by default for OSS platforms
    assert config.cleanup_repo is True


def test_dev_bounty_pipeline_config_custom():
    """Test custom configuration."""
    config = DevBountyPipelineConfig(
        clone_timeout=60,
        min_test_pass_rate=0.9,
        auto_submit=True,
        freelancer_token="test_token",
    )
    assert config.clone_timeout == 60
    assert config.min_test_pass_rate == 0.9
    assert config.auto_submit is True
    assert config.freelancer_token == "test_token"


def test_dev_bounty_pipeline_executors_initialized():
    """Test all executors are initialized."""
    pipeline = DevBountyPipeline()
    assert "freelancer" in pipeline.executors
    assert "opire" in pipeline.executors
    assert "issuehunt" in pipeline.executors
    assert "mindrift" in pipeline.executors
    assert "outlier" in pipeline.executors


def test_get_executor_known_platforms():
    """Test getting executors for known platforms."""
    pipeline = DevBountyPipeline()
    assert pipeline._get_executor("freelancer") is not None
    assert pipeline._get_executor("opire") is not None
    assert pipeline._get_executor("issuehunt") is not None
    assert pipeline._get_executor("mindrift") is not None
    assert pipeline._get_executor("outlier") is not None


def test_get_executor_unknown_platform():
    """Test getting executor for unknown platform returns None."""
    pipeline = DevBountyPipeline()
    assert pipeline._get_executor("unknown") is None
    assert pipeline._get_executor("") is None


def test_dev_bounty_pipeline_result_structure():
    """Test result dataclass structure."""
    from core.autonomy.dev_bounty_pipeline import DevBountyPipelineResult

    result = DevBountyPipelineResult(
        success=True,
        bounty_id="test_123",
        platform="opire",
        verdict="submitted",
    )
    assert result.success is True
    assert result.bounty_id == "test_123"
    assert result.platform == "opire"
    assert result.verdict == "submitted"
    assert result.total_duration_seconds == 0.0
    assert result.phases == {}
    assert result.error is None
