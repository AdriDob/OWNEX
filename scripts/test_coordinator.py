#!/usr/bin/env python3
"""Test script for BountyCoordinator."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ruff: noqa: E402
from cores.agents.bounty_coordinator import CoordinatorConfig, get_bounty_coordinator


async def test_coordinator():
    """Test basic coordinator functionality."""
    print("Testing BountyCoordinator...")

    # Get coordinator instance
    coordinator = get_bounty_coordinator(
        CoordinatorConfig(
            max_concurrent=2,
            timeout_minutes=30,
            auto_start=False,
            enable_priority_queue=True,
            cleanup_on_failure=True,
        )
    )

    # Test 1: Start coordinator
    print("\n1. Starting coordinator...")
    result = coordinator.start()
    print(f"   Result: {result}")
    assert result["status"] == "started", "Failed to start coordinator"

    # Test 2: Add bounties to queue
    print("\n2. Adding bounties to queue...")
    bounty1 = coordinator.add_bounty(
        bounty_id="test-bounty-1",
        repo="owner/repo1",
        issue_number=101,
        issue_url="https://github.com/owner/repo1/issues/101",
        title="Fix bug in authentication",
        description="Authentication fails when...",
        evh=150.0,
    )
    print(f"   Bounty 1: {bounty1}")

    bounty2 = coordinator.add_bounty(
        bounty_id="test-bounty-2",
        repo="owner/repo2",
        issue_number=202,
        issue_url="https://github.com/owner/repo2/issues/202",
        title="Add feature X",
        description="Need to add feature X for...",
        evh=75.0,
    )
    print(f"   Bounty 2: {bounty2}")

    bounty3 = coordinator.add_bounty(
        bounty_id="test-bounty-3",
        repo="owner/repo3",
        issue_number=303,
        issue_url="https://github.com/owner/repo3/issues/303",
        title="Refactor code",
        description="Refactor the codebase to...",
        evh=200.0,
    )
    print(f"   Bounty 3: {bounty3}")

    # Test 3: Get status
    print("\n3. Getting coordinator status...")
    status = coordinator.get_status()
    print(f"   Running: {status['running']}")
    print(f"   Queue size: {status['queue']['queued']}")
    print(f"   Active count: {status['queue']['active']}")
    print(f"   Completed count: {status['queue']['completed']}")

    # Test 4: Stop coordinator
    print("\n4. Stopping coordinator...")
    result = coordinator.stop()
    print(f"   Result: {result}")
    assert result["status"] == "stopped", "Failed to stop coordinator"

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_coordinator())
