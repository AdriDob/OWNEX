"""Tests for Polar.sh adapter (honest-empty: seed URL 404, no seeds)."""

from __future__ import annotations

import pytest

from api.adapters.direct_work_polar import PolarAdapter, build_polar_adapter


def test_polar_adapter_build():
    adapter = build_polar_adapter()
    assert isinstance(adapter, PolarAdapter)
    assert adapter.name == "polar"


def test_polar_seeds_empty():
    # /rust-analyzer verificado 404 (2026-09-16): sin seeds hasta URL viva.
    assert PolarAdapter.CURATED_BOUNTIES == []


@pytest.mark.asyncio
async def test_polar_fetch_empty_honest():
    adapter = build_polar_adapter()
    assert await adapter.fetch_opportunities() == []
