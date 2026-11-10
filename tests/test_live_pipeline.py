"""Tests for the live opportunity pipeline (fixture-driven, no network)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cores.opportunity.live_pipeline import (
    LIVE_FETCHERS,
    LiveOpportunity,
    LiveStore,
    _platform_for,
    _to_live,
    get_live_opportunities,
    live_opportunity_stats,
    run_live_scan,
)


@pytest.fixture
def store(tmp_path: Path) -> LiveStore:
    return LiveStore(tmp_path / "live.json")


def _raw(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "algora_123",
        "name": "Fix bug in parser",
        "description": "desc",
        "platform": "algora",
        "url": "https://algora.io/bounties/123",
        "reward": 50.0,
        "effort_hours": 2.0,
        "tags": ["python"],
        "cycle": "forge",
        "source_type": "dev_bounty",
        "source_name": "algora",
        "metadata": {},
    }
    base.update(overrides)
    return base


class TestNormalization:
    def test_to_live_maps_fields(self):
        opp = _to_live("algora", _raw())
        assert opp is not None
        assert opp.platform == "algora"
        assert opp.reward == 50.0
        assert opp.status == "discovered"
        assert opp.evidence_url == "https://algora.io/bounties/123"
        assert opp.dedup_key() == "algora:algora_123"

    def test_to_live_skips_missing_id(self):
        assert _to_live("algora", {"name": "x"}) is None

    def test_platform_upwork_excluded(self):
        assert _platform_for({"platform": "upwork"}) == "other"
        assert _to_live("x", _raw(platform="upwork", id="u1")) is not None  # maps to other
        opp = _to_live("x", _raw(platform="upwork", id="u2"))
        assert opp is not None and opp.platform == "other"

    def test_github_source_name_refines_platform(self):
        raw = _raw(platform="github", source_name="github_algora")
        assert _platform_for(raw) == "algora"


class TestStore:
    def test_upsert_new_and_refresh(self, store):
        opp = _to_live("algora", _raw())
        assert store is not None and opp is not None
        assert store.upsert(opp) is True
        assert store.upsert(_to_live("algora", _raw(reward=75.0))) is False
        items = store.all()
        assert len(items) == 1
        assert items[0].reward == 75.0  # refreshed mutable field

    def test_dedup_key_isolation(self, store):
        store.upsert(LiveOpportunity(id="1", platform="algora", adapter="a", title="t", url="u"))
        store.upsert(LiveOpportunity(id="1", platform="opire", adapter="a", title="t", url="u"))
        assert len(store.all()) == 2

    def test_mark_expired_missing(self, store):
        store.upsert(LiveOpportunity(id="1", platform="algora", adapter="a", title="t", url="u"))
        store.upsert(LiveOpportunity(id="2", platform="opire", adapter="a", title="t", url="u"))
        expired = store.mark_expired_missing({"algora:1"})
        assert expired == 1
        assert store.all(status="expired")[0].id == "2"

    def test_persistence_roundtrip(self, store, tmp_path):
        store.upsert(LiveOpportunity(id="1", platform="algora", adapter="a", title="t", url="u", reward=10.0))
        store.save()
        store2 = LiveStore(tmp_path / "live.json")
        assert store2.stats()["total"] == 1
        assert store2.all()[0].reward == 10.0


class TestScan:
    @pytest.mark.asyncio
    async def test_run_live_scan_with_fixture_fetcher(self, store, monkeypatch):
        async def fake_fetch():
            return [_raw(), _raw(id="algora_124")]

        import core.opportunity.adapters.forge.algora as algora_mod

        monkeypatch.setattr(algora_mod, "fetch_opportunities", fake_fetch)
        # Restrict scan to one fetcher for determinism
        report = await run_live_scan(fetchers=["algora"], store=store)
        assert report["new_opportunities"] == 2
        assert report["errors"] == []
        assert report["stats"]["total"] == 2

    @pytest.mark.asyncio
    async def test_run_live_scan_reports_errors(self, store, monkeypatch):
        async def boom():
            raise RuntimeError("endpoint down")

        import core.opportunity.adapters.forge.opire as opire_mod

        monkeypatch.setattr(opire_mod, "fetch_opportunities", boom)
        report = await run_live_scan(fetchers=["opire"], store=store)
        assert report["new_opportunities"] == 0
        assert len(report["errors"]) == 1
        assert "opire" in report["errors"][0]

    @pytest.mark.asyncio
    async def test_upwork_never_persisted(self, store, monkeypatch):
        async def fake_fetch():
            return [_raw(platform="upwork", id="u1"), _raw(id="algora_ok")]

        import core.opportunity.adapters.forge.algora as algora_mod

        monkeypatch.setattr(algora_mod, "fetch_opportunities", fake_fetch)
        await run_live_scan(fetchers=["algora"], store=store)
        platforms = {i.platform for i in store.all()}
        assert "upwork" not in platforms


class TestReadback:
    def test_get_live_opportunities_filters(self, store):
        store.upsert(LiveOpportunity(id="1", platform="algora", adapter="a", title="t", url="u"))
        store.upsert(LiveOpportunity(id="2", platform="opire", adapter="a", title="t", url="u", status="expired"))
        assert len(get_live_opportunities(store=store)) == 2
        assert len(get_live_opportunities(status="expired", store=store)) == 1
        assert len(get_live_opportunities(platform="algora", store=store)) == 1

    def test_stats_shape(self, store):
        store.upsert(LiveOpportunity(id="1", platform="algora", adapter="a", title="t", url="u"))
        stats = live_opportunity_stats(store)
        assert stats["total"] == 1
        assert "algora" in stats["fetchers_available"]
        assert "upwork" in stats["excluded_platforms"]


def test_fetchers_map_resolves():
    for key, spec in LIVE_FETCHERS.items():
        module_path, _, attr = spec.partition(":")
        assert module_path.startswith("core.opportunity.adapters.forge."), key
        assert attr == "fetch_opportunities"


class TestDweBridge:
    def test_to_dwe_opportunity(self):
        opp = _to_live("algora", _raw())
        assert opp is not None
        from cores.opportunity.live_pipeline import to_dwe_opportunity

        dwe = to_dwe_opportunity(opp)
        assert dwe.id == "live:algora:algora_123"
        assert dwe.payment == 50.0
        assert str(dwe.platform) == "algora" or dwe.platform.value == "algora"

    def test_live_candidates_and_mark_ready(self, store):
        store.upsert(_to_live("algora", _raw()) or LiveOpportunity(id="x", platform="algora", adapter="a", title="t", url="u"))
        from cores.opportunity.live_pipeline import (
            live_candidates_for_workbank,
            mark_ready_from_workbank,
        )

        candidates = live_candidates_for_workbank(store=store)
        assert len(candidates) == 1

        # Simulate workbank accepting the item id
        class FakeItem:
            opportunity_id = candidates[0].id

        assert mark_ready_from_workbank([FakeItem()], store) == 1
        assert store.all(status="ready")[0].platform == "algora"


class TestSecurityBridge:
    @pytest.mark.asyncio
    async def test_class_fetcher_resolves_and_normalizes(self, store, monkeypatch):
        """Class-based OpportunityAdapter specs instantiate + return RawOpportunity."""
        from dataclasses import dataclass

        @dataclass
        class FakeRaw:
            id: str
            name: str
            platform: str
            url: str
            reward: float = 100.0
            cycle: str = "security"
            source_type: str = "platform"
            source_name: str = "hackerone"
            description: str = ""
            effort_hours: float = 4.0
            tags: list = None
            metadata: dict = None
            created_at: str = ""

        class FakeAdapter:
            def __init__(self):
                pass

            async def fetch_opportunities(self, personal=None):
                return [FakeRaw(id="h1", name="Program", platform="hackerone", url="https://hackerone.com/x")]

        import sys
        import types

        mod = types.ModuleType("fake_sec_mod")
        mod.FakeSecAdapter = FakeAdapter
        monkeypatch.setitem(sys.modules, "fake_sec_mod", mod)

        from cores.opportunity import live_pipeline as lp

        monkeypatch.setattr(lp, "SECURITY_FETCHERS", {"fakesec": "fake_sec_mod:FakeSecAdapter"})
        report = await lp.run_live_scan(fetchers=["fakesec"], store=store)
        assert report["new_opportunities"] == 1
        opp = store.all()[0]
        assert opp.platform == "hackerone"
        assert opp.category == "security"

    @pytest.mark.asyncio
    async def test_partial_scan_does_not_expire_unscanned(self, store, monkeypatch):
        """Scanning one fetcher must not expire items from other adapters."""
        store.upsert(LiveOpportunity(id="1", platform="algora", adapter="github_bounties", title="t", url="u"))
        store.upsert(LiveOpportunity(id="2", platform="opire", adapter="opire", title="t", url="u"))

        import core.opportunity.adapters.forge.opire as opire_mod

        async def empty():
            return []

        monkeypatch.setattr(opire_mod, "fetch_opportunities", empty)
        report = await run_live_scan(fetchers=["opire"], store=store)
        assert report["marked_expired"] == 1  # only the opire item
        by_id = {i.id: i for i in store.all()}
        assert by_id["1"].status == "discovered"  # github_bounties item untouched
        assert by_id["2"].status == "expired"

    def test_expired_item_revives_on_refetch(self, store):
        opp = LiveOpportunity(id="1", platform="algora", adapter="a", title="t", url="u", status="expired")
        store.upsert(opp)
        store.upsert(LiveOpportunity(id="1", platform="algora", adapter="a", title="t", url="u"))
        assert store.all()[0].status == "discovered"


class TestEligibility:
    def _fake_src(self, **kw):
        class S:
            pass

        s = S()
        s.name = kw.pop("name", "Algora")
        for k, v in kw.items():
            setattr(s, k, v)
        return s

    def test_evaluate_with_catalog_match(self):
        from cores.opportunity.live_pipeline import evaluate_eligibility

        opp = _to_live("algora", _raw())
        catalog = {
            "algora": self._fake_src(
                name="Algora",
                argentina_ok=True,
                requires_account=True,
                requires_interview=False,
                requires_experience=False,
                requires_portfolio=False,
                requires_assessment=False,
            )
        }
        report = evaluate_eligibility(opp, catalog)
        assert report["argentina_compatible"] == "yes"
        assert report["requires_interview"] == "no"
        assert report["evidence"].startswith("catalog:")
        assert report["blockers"] == []

    def test_evaluate_no_match_stays_unknown(self):
        from cores.opportunity.live_pipeline import evaluate_eligibility

        opp = _to_live("algora", _raw())
        report = evaluate_eligibility(opp, {})
        assert report["argentina_compatible"] == "unknown"
        assert report["evidence"] == "no_catalog_match"

    def test_blocker_when_no_argentina_no_payment(self):
        from cores.opportunity.live_pipeline import evaluate_eligibility

        opp = _to_live("algora", _raw())
        catalog = {"algora": self._fake_src(name="Algora", argentina_ok=False)}
        report = evaluate_eligibility(opp, catalog)
        assert "no_argentina_path" in report["blockers"]

    def test_run_eligibility_transitions_status(self, store, monkeypatch):
        from cores.opportunity import live_pipeline as lp

        monkeypatch.setattr(lp, "_catalog_index", lambda: {})
        opp = _to_live("algora", _raw())
        assert opp is not None
        store.upsert(opp)
        # Empty catalog → nothing matches → stays discovered
        lp.run_eligibility_check(store)
        assert store.all()[0].status == "discovered"

    def test_run_eligibility_with_match_moves_status(self, store, monkeypatch):
        from cores.opportunity import live_pipeline as lp

        src = self._fake_src(name="Algora", argentina_ok=True)
        monkeypatch.setattr(lp, "_catalog_index", lambda: {"algora": src})
        opp = _to_live("algora", _raw())
        assert opp is not None
        store.upsert(opp)
        report = lp.run_eligibility_check(store)
        assert report["moved_to_eligibility_checked"] == 1
        item = store.all()[0]
        assert item.status == "eligibility_checked"
        assert item.raw["eligibility"]["argentina_compatible"] == "yes"
