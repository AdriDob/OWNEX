"""Tests for Polar.sh adapter."""

from __future__ import annotations

import pytest

from api.adapters.direct_work_polar import PolarAdapter, build_polar_adapter
from cores.direct_work_engine.models import WorkPlatform


def test_polar_adapter_build():
    adapter = build_polar_adapter()
    assert isinstance(adapter, PolarAdapter)
    assert adapter.name == "polar"


@pytest.mark.asyncio
async def test_polar_fetch_opportunities():
    adapter = build_polar_adapter()
    opportunities = await adapter.fetch_opportunities()

    assert len(opportunities) > 0
    assert all(opp.platform == WorkPlatform.POLAR for opp in opportunities)
    assert all(opp.payment > 0 for opp in opportunities)
    assert all(opp.employment_type.value == "contract" for opp in opportunities)
    assert all(opp.interview_required is False for opp in opportunities)
    assert all(opp.portfolio_required is False for opp in opportunities)


@pytest.mark.asyncio
async def test_polar_curated_bounties_structure():
    adapter = build_polar_adapter()
    opportunities = await adapter.fetch_opportunities()

    # Verify curated bounties have required fields
    for opp in opportunities:
        assert opp.id.startswith("polar_")
        assert opp.url.startswith("https://polar.sh/")
        assert opp.technology_tags  # Should have technology tags
        assert opp.payment_method.value == "platform_credit"
        assert opp.difficulty.value in ["BEGINNER", "INTERMEDIATE", "ADVANCED"]
