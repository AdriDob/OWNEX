"""L6: Toloka/Prolific/Clickworker — keyed live fetch or curated fallback, manual apply."""

from __future__ import annotations

import pytest

from cores.opportunity.adapters.microtask import (
    ClickworkerAdapter,
    ProlificAdapter,
    TolokaAdapter,
)


class TestCuratedFallback:
    @pytest.mark.asyncio()
    async def test_no_key_returns_curated(self):
        for cls in (TolokaAdapter, ProlificAdapter, ClickworkerAdapter):
            opps = await cls(config={}).fetch_opportunities()
            assert len(opps) >= 1
            assert all(o.metadata.get("apply") == "MANUAL" for o in opps)
            assert all((o.url or "").startswith("https://") for o in opps)
            assert all(o.reward == 0.0 for o in opps)

    def test_clickworker_always_curated(self):
        import asyncio

        opps = asyncio.run(ClickworkerAdapter().fetch_opportunities())
        assert all(o.metadata.get("live") is False for o in opps)


class TestLivePath:
    @pytest.mark.asyncio()
    async def test_toloka_keyed_parses_pools(self, monkeypatch):
        import httpx

        class _Resp:
            status_code = 200

            def json(self):
                return {"items": [{"id": "p1", "private_name": "Image labeling"}]}

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
        opps = await TolokaAdapter(config={"api_key": "k"}).fetch_opportunities()
        assert len(opps) == 1
        assert opps[0].id == "toloka_p1"
        assert opps[0].metadata.get("live") is True
        assert opps[0].metadata.get("apply") == "MANUAL"

    @pytest.mark.asyncio()
    async def test_prolific_keyed_parses_studies(self, monkeypatch):
        import httpx

        class _Resp:
            status_code = 200

            def json(self):
                return {"results": [{"id": "s1", "name": "Decision study", "reward": 12.5}]}

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
        opps = await ProlificAdapter(config={"token": "k"}).fetch_opportunities()
        assert len(opps) == 1
        assert opps[0].reward == 12.5

    @pytest.mark.asyncio()
    async def test_bad_status_falls_back(self, monkeypatch):
        import httpx

        class _Resp:
            status_code = 401

            def json(self):
                return {}

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
        opps = await TolokaAdapter(config={"api_key": "bad"}).fetch_opportunities()
        assert len(opps) >= 1
        assert all(o.metadata.get("live") is not True for o in opps)


class TestRegistration:
    def test_registry_has_microtask_boards(self):
        from cores.opportunity.adapters import get_adapter_registry

        reg = get_adapter_registry()
        for key in ("toloka", "prolific", "clickworker"):
            assert reg.get(key) is not None, key
