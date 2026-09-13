"""Tests for BountyBoard.dev adapter."""

from __future__ import annotations

import pytest

from api.adapters.direct_work_bountyboard import BountyBoardAdapter, build_bountyboard_adapter
from cores.direct_work_engine.models import WorkPlatform


def test_bountyboard_adapter_build():
    adapter = build_bountyboard_adapter()
    assert isinstance(adapter, BountyBoardAdapter)
    assert adapter.name == "bountyboard"


@pytest.mark.asyncio
async def test_bountyboard_fetch_opportunities():
    adapter = build_bountyboard_adapter()
    opportunities = await adapter.fetch_opportunities()

    assert len(opportunities) > 0
    assert all(opp.platform == WorkPlatform.BOUNTYBOARD for opp in opportunities)
    assert all(opp.payment > 0 for opp in opportunities)
    assert all(opp.employment_type.value == "contract" for opp in opportunities)
    assert all(opp.interview_required is False for opp in opportunities)
    assert all(opp.portfolio_required is False for opp in opportunities)


@pytest.mark.asyncio
async def test_bountyboard_curated_bounties_structure():
    adapter = build_bountyboard_adapter()
    opportunities = await adapter.fetch_opportunities()

    # Verify curated bounties have required fields
    for opp in opportunities:
        assert opp.id.startswith("bountyboard_")
        assert opp.url.startswith("https://bountyboard.dev/")
        assert opp.technology_tags  # Should have technology tags
        assert opp.payment_method.value == "platform_credit"
        assert opp.difficulty.value in ["BEGINNER", "INTERMEDIATE", "ADVANCED"]
