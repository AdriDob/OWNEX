"""Tests for BountyBoard.dev adapter (honest-empty: site down, no seeds)."""

from __future__ import annotations

import pytest

from api.adapters.direct_work_bountyboard import BountyBoardAdapter, build_bountyboard_adapter


def test_bountyboard_adapter_build():
    adapter = build_bountyboard_adapter()
    assert isinstance(adapter, BountyBoardAdapter)
    assert adapter.name == "bountyboard"


def test_bountyboard_seeds_empty():
    # bountyboard.dev verificado caído (2026-09-16): sin seeds hasta URL viva.
    assert BountyBoardAdapter.CURATED_BOUNTIES == []


@pytest.mark.asyncio
async def test_bountyboard_fetch_empty_honest():
    adapter = build_bountyboard_adapter()
    assert await adapter.fetch_opportunities() == []
