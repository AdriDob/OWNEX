"""L5: AR job boards (ZonaJobs/Bumeran/Computrabajo) — read-only, manual apply."""

from __future__ import annotations

import pytest

from cores.direct_work_engine.category_funnel import funnel_for_category
from cores.direct_work_engine.models import OpportunityCategory
from cores.opportunity.adapters.ar_jobs import (
    BumeranAdapter,
    ComputrabajoAdapter,
    ZonaJobsAdapter,
    build_ar_search_url,
)


class TestCuratedFallback:
    @pytest.mark.asyncio()
    async def test_network_failure_returns_curated(self, monkeypatch):
        import httpx

        async def _boom(*args, **kwargs):
            raise httpx.ConnectError("no network")

        monkeypatch.setattr(httpx.AsyncClient, "get", _boom)
        opps = await ZonaJobsAdapter().fetch_opportunities()
        assert len(opps) == 2
        assert all(o.metadata.get("apply") == "MANUAL" for o in opps)
        assert all((o.url or "").startswith("https://") for o in opps)

    @pytest.mark.asyncio()
    async def test_zone_filters_curated(self, monkeypatch):
        import httpx

        async def _boom(*args, **kwargs):
            raise httpx.ConnectError("no network")

        monkeypatch.setattr(httpx.AsyncClient, "get", _boom)
        opps = await BumeranAdapter(config={"zone": "Zona Sur"}).fetch_opportunities()
        assert len(opps) == 1
        assert "Zona Sur" in opps[0].name

    def test_no_reward_invented(self):
        import asyncio

        async def _boom(*args, **kwargs):
            raise RuntimeError("x")

        import httpx

        orig = httpx.AsyncClient.get

        async def go():
            try:
                httpx.AsyncClient.get = _boom
                return await ComputrabajoAdapter().fetch_opportunities()
            finally:
                httpx.AsyncClient.get = orig

        opps = asyncio.run(go())
        assert all(o.reward == 0.0 for o in opps)


class TestParse:
    @pytest.mark.asyncio()
    async def test_best_effort_parse(self, monkeypatch):
        import httpx

        html = (
            '<h2><a href="/ofertas-de-trabajo/junior-dev-123">Junior Dev CABA</a></h2>'
            '<h2><a href="/empleos/qa-456">QA Sr Zona Sur</a></h2>'
        )

        class _Resp:
            status_code = 200
            text = html

        class _Client:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, *a, **k):
                return _Resp()

        monkeypatch.setattr(httpx, "AsyncClient", _Client)
        opps = await ZonaJobsAdapter().fetch_opportunities()
        assert len(opps) == 2
        assert opps[0].metadata.get("apply") == "MANUAL"
        assert opps[0].metadata.get("modality") == "presencial"
        assert opps[0].metadata.get("interview_required") is True

    @pytest.mark.asyncio()
    async def test_garbage_html_falls_back(self, monkeypatch):
        import httpx

        class _Resp:
            status_code = 200
            text = "<html><body>nothing here</body></html>"

        class _Client:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, *a, **k):
                return _Resp()

        monkeypatch.setattr(httpx, "AsyncClient", _Client)
        opps = await ComputrabajoAdapter().fetch_opportunities()
        assert len(opps) == 2  # curated fallback
        assert all(o.metadata.get("apply") == "MANUAL" for o in opps)


class TestWiring:
    def test_employment_category_and_funnel(self):
        assert OpportunityCategory.EMPLOYMENT.value == "employment"
        assert funnel_for_category(OpportunityCategory.EMPLOYMENT) == "employment"
        assert funnel_for_category("employment") == "employment"

    def test_registry_has_ar_boards(self):
        from cores.opportunity.adapters import get_adapter_registry

        reg = get_adapter_registry()
        for key in ("zonajobs", "bumeran", "computrabajo"):
            assert reg.get(key) is not None, key

    def test_search_url_builder(self):
        url = build_ar_search_url("zonajobs", "junior developer", "Zona Sur")
        assert "zonajobs.com.ar" in url
        assert "Zona+Sur" in url or "Zona%20Sur" in url

    def test_converter_metadata_overrides(self, monkeypatch):
        import asyncio

        import httpx

        from api.adapters.legacy import LegacyOpportunityDweAdapter
        from cores.direct_work_engine.models import EmploymentType, Modality, WorkPlatform

        async def _boom(*args, **kwargs):
            raise httpx.ConnectError("no network")

        monkeypatch.setattr(httpx.AsyncClient, "get", _boom)

        async def go():
            adapter = LegacyOpportunityDweAdapter(
                ZonaJobsAdapter(),
                name="zonajobs",
                platform=WorkPlatform.ZONAJOBS,
                category=OpportunityCategory.EMPLOYMENT,
                employment_type=EmploymentType.FULL_TIME,
            )
            raw = (await ZonaJobsAdapter().fetch_opportunities())[0]
            return [adapter._convert(raw)]

        opp = asyncio.run(go())[0]
        assert opp.modality == Modality.PRESENCIAL
        assert opp.interview_required is True
        assert opp.region == "AR"
        assert opp.category == OpportunityCategory.EMPLOYMENT
