"""Tests for Algora.io adapter."""

from __future__ import annotations

import pytest

from api.adapters.direct_work_algora import AlgoraAdapter, build_algora_adapter
from cores.direct_work_engine.models import WorkPlatform


def test_algora_adapter_build():
    adapter = build_algora_adapter()
    assert isinstance(adapter, AlgoraAdapter)
    assert adapter.name == "algora"


@pytest.mark.asyncio
async def test_algora_fetch_opportunities():
    adapter = build_algora_adapter()
    opportunities = await adapter.fetch_opportunities()

    assert len(opportunities) > 0
    assert all(opp.platform == WorkPlatform.ALGORA for opp in opportunities)
    assert all(opp.payment > 0 for opp in opportunities)
    assert all(opp.employment_type.value == "contract" for opp in opportunities)
    assert all(opp.interview_required is False for opp in opportunities)
    assert all(opp.portfolio_required is False for opp in opportunities)


@pytest.mark.asyncio
async def test_algora_curated_bounties_structure():
    adapter = build_algora_adapter()
    opportunities = await adapter.fetch_opportunities()

    # Verify curated bounties have required fields
    for opp in opportunities:
        assert opp.id.startswith("algora_")
        assert opp.url.startswith("https://algora.io/")
        assert opp.technology_tags  # Should have technology tags
        assert opp.payment_method.value == "platform_credit"
        assert opp.difficulty.value in ["BEGINNER", "INTERMEDIATE", "ADVANCED"]
