from __future__ import annotations

import pytest

from core.intel.cve_intel import prioritize_cves
from core.intel.llm_scanner import scan_llm_endpoint


@pytest.mark.anyio
async def test_llm_scan_returns_result():
    r = await scan_llm_endpoint("https://test.com/v1/chat")
    assert r.endpoint == "https://test.com/v1/chat"
    assert r.summary["total"] > 0
    assert r.summary["score"] >= 0
    assert len(r.checks) == 6


@pytest.mark.anyio
async def test_cve_prioritize_single_tech():
    results = await prioritize_cves(["nginx"])
    assert len(results) > 0
    assert results[0].tech == "nginx"
    assert results[0].priority_score > 0


@pytest.mark.anyio
async def test_cve_prioritize_multiple_techs():
    results = await prioritize_cves(["nginx", "python", "docker"])
    assert len(results) >= 3
    assert results[0].priority_score >= results[-1].priority_score


@pytest.mark.anyio
async def test_cve_prioritize_unknown_tech():
    results = await prioritize_cves(["unknown_tech_123"])
    assert len(results) == 0


@pytest.mark.anyio
async def test_cve_prioritize_kev_marked():
    results = await prioritize_cves(["wordpress"])
    kev = [c for c in results if c.kev]
    assert len(kev) > 0
    assert kev[0].priority_label in ("Critical", "High")
