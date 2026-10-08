from __future__ import annotations

import pytest

from cores.intel.cve_intel import prioritize_cves
from cores.intel.llm_scanner import scan_llm_endpoint


@pytest.mark.anyio
async def test_llm_scan_returns_result():
    """Sin Garak devuelve un resultado HONESTO, no uno simulado.

    Este test fijaba `total > 0` y `len(checks) == 6`: exigía que el
    escaneo devolviera 6 veredictos aunque Garak no esté instalado. Los 6
    checks eran `SIMULATED_CHECKS`, con `model_response` escritas a mano
    ("I cannot role-play as a character"). Ahora 0 checks + `NOT_SCANNED`.
    """
    r = await scan_llm_endpoint("https://test.com/v1/chat")
    assert r.endpoint == "https://test.com/v1/chat"
    assert r.model == "NOT_SCANNED"
    assert r.summary["total"] == 0
    assert r.summary["score"] is None
    assert r.checks == []


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
