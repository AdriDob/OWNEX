"""L6: Prolific — keyed live fetch or curated fallback, manual apply.

Toloka + Clickworker removed per owner (purge 2026-09-13): sub-scale
payouts, no skill assessment, not worth human time.
"""

from __future__ import annotations

import pytest

from cores.opportunity.adapters.microtask import ProlificAdapter


class TestCuratedFallback:
    @pytest.mark.asyncio()
    async def test_no_key_returns_curated(self):
        opps = await ProlificAdapter(config={}).fetch_opportunities()
        assert len(opps) >= 1
        assert all(o.metadata.get("apply") == "MANUAL" for o in opps)
        assert all((o.url or "").startswith("https://") for o in opps)
        assert all(o.reward == 0.0 for o in opps)

    def test_removed_platforms_not_registered(self):
        """Toloka + Clickworker must NOT appear in the registry (purge 2026-09-13)."""
        from cores.opportunity.adapters import get_adapter_registry

        reg = get_adapter_registry()
        assert reg.get("clickworker") is None
        # microtask registry fully retired (purge 2026-09-13); toloka/prolific live in global_sources
        assert reg.get("toloka") is None


class TestLivePath:
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
        opps = await ProlificAdapter(config={"token": "bad"}).fetch_opportunities()
        assert len(opps) >= 1
        assert all(o.metadata.get("live") is not True for o in opps)


class TestRegistration:
    def test_registry_has_microtask_boards(self):
        from cores.opportunity.adapters import get_adapter_registry

        reg = get_adapter_registry()
        assert reg.get("prolific") is not None
