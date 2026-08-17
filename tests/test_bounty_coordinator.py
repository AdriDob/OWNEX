"""Tests for BountyCoordinator integration with scheduler."""

import pytest

from cores.agents.bounty_coordinator import (
    BountyCoordinator,
    CoordinatorConfig,
    get_bounty_coordinator,
    run_coordinator_cycle,
)
from cores.opportunity.models import Opportunity, OpportunitySource


def _make_opportunity(bounty_id: str) -> Opportunity:
    return Opportunity(
        id=bounty_id,
        name=f"Test Bounty {bounty_id}",
        source=OpportunitySource(
            type="platform",
            name="algora",
            url="https://algora.io/issue/example",
            confidence=0.8,
        ),
        category="oss",
        public_url="https://algora.io/issue/example",
        estimated_payout=300.0,
        estimated_effort_hours=2.0,
    )


def test_coordinator_singleton():
    """Test that coordinator is a singleton."""
    coord1 = get_bounty_coordinator()
    coord2 = get_bounty_coordinator()
    assert coord1 is coord2


def test_coordinator_initialization():
    """Test coordinator initialization with default config."""
    coord = BountyCoordinator()
    assert coord.config.max_concurrent == 3
    assert coord.config.timeout_minutes == 30
    assert coord.config.auto_start is False
    assert not coord.is_running()


def test_coordinator_custom_config():
    """Test coordinator initialization with custom config."""
    config = CoordinatorConfig(
        max_concurrent=5,
        timeout_minutes=45,
        auto_start=True,
    )
    coord = BountyCoordinator(config)
    assert coord.config.max_concurrent == 5
    assert coord.config.timeout_minutes == 45
    assert coord.config.auto_start is True


def test_coordinator_is_running():
    """Test is_running method."""
    coord = BountyCoordinator()
    assert not coord.is_running()

    # Start coordinator
    coord.start()
    assert coord.is_running()

    # Stop coordinator
    coord.stop()
    assert not coord.is_running()


def test_add_bounty_simple():
    """Test adding a bounty with simplified signature."""
    coord = BountyCoordinator()

    opp = _make_opportunity("test_bounty_1")

    result = coord.add_bounty_simple("test_bounty_1", opp)
    assert result["status"] == "queued"
    assert result["bounty_id"] == "test_bounty_1"
    assert result["evh"] > 0  # EVH should be calculated


def test_coordinator_get_status():
    """Test getting coordinator status."""
    coord = BountyCoordinator()

    opp = _make_opportunity("test_bounty_2")

    coord.add_bounty_simple("test_bounty_2", opp)

    status = coord.get_status()
    assert "running" in status
    assert "queue" in status
    assert "queued" in status["queue"]
    assert "active" in status["queue"]
    assert "completed" in status["queue"]
    assert status["queue"]["queued"] >= 1


def test_run_coordinator_cycle():
    """Test the scheduler job handler."""
    result = run_coordinator_cycle()
    assert result is not None
    assert "success" in result
    assert "status" in result


def test_coordinator_start_stop():
    """Test starting and stopping coordinator."""
    coord = BountyCoordinator()

    # Start
    start_result = coord.start()
    assert start_result["status"] == "started"
    assert coord.is_running()

    # Stop
    stop_result = coord.stop()
    assert stop_result["status"] == "stopped"
    assert not coord.is_running()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
