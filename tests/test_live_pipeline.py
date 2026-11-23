"""Tests for the live opportunity pipeline (fixture-driven, no network)."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace
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
    platform_track_record,
    run_live_scan,
    score_opportunity,
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
        assert module_path.startswith("core.opportunity.adapters."), key
        module = importlib.import_module(module_path)
        assert hasattr(module, attr), key


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


class TestWorkbankPromotion:
    def test_candidates_include_eligibility_checked(self, store):
        from cores.opportunity.live_pipeline import live_candidates_for_workbank

        store.upsert(LiveOpportunity(id="1", platform="algora", adapter="a", title="t", url="u", status="eligibility_checked"))
        store.upsert(LiveOpportunity(id="2", platform="opire", adapter="a", title="t", url="u", status="ready"))
        cands = live_candidates_for_workbank(store=store)
        assert len(cands) == 1  # ready excluded, eligibility_checked included

    def test_mark_ready_accepts_eligibility_checked(self, store):
        from types import SimpleNamespace

        from cores.opportunity.live_pipeline import mark_ready_from_workbank

        store.upsert(LiveOpportunity(id="1", platform="algora", adapter="a", title="t", url="u", status="eligibility_checked"))
        n = mark_ready_from_workbank([SimpleNamespace(id="live:algora:1")], store)
        assert n == 1
        assert store.all(status="ready")


class TestEthicsAndPrepare:
    def test_ethics_screen_catches_captcha(self):
        from cores.opportunity.live_pipeline import ethics_screen

        opp = LiveOpportunity(id="1", platform="opire", adapter="a", title="Auto Solve hcapcha", url="u")
        assert ethics_screen(opp)

    def test_ethics_screen_allows_security_work(self):
        from cores.opportunity.live_pipeline import ethics_screen

        opp = LiveOpportunity(id="1", platform="hackerone", adapter="a", title="API Security Assessment - auth bypass testing", url="u")
        assert ethics_screen(opp) == []

    def test_prepare_execution_marks_in_progress(self, store, tmp_path):
        import asyncio

        from cores.opportunity.live_pipeline import prepare_execution

        opp = _to_live("algora", _raw())
        assert opp is not None
        opp.status = "ready"
        store.upsert(opp)
        result = asyncio.run(prepare_execution(opp.dedup_key(), store, tmp_path))
        assert result["status"] == "in_progress"
        assert (tmp_path / result["workspace"].split("/")[-1] / "ISSUE.md").exists()
        assert store.all(status="in_progress")

    def test_prepare_rejects_ethics_blocked(self, store, tmp_path):
        import asyncio

        from cores.opportunity.live_pipeline import prepare_execution

        opp = LiveOpportunity(id="1", platform="opire", adapter="a", title="Solve hcaptcha for pay", url="u", status="ready")
        store.upsert(opp)
        result = asyncio.run(prepare_execution(opp.dedup_key(), store, tmp_path))
        assert result["error"] == "ethics_screen"
        assert store.all(status="rejected")

    def test_prepare_writes_plan_and_estimate(self, store, tmp_path):
        import asyncio
        import json

        from cores.opportunity.live_pipeline import LiveOpportunity, prepare_execution

        opp = LiveOpportunity(
            id="p1",
            platform="issuehunt",
            adapter="a",
            title="Fix good first issue: typo in docs",
            url="https://example.com/task",
            reward=50.0,
            currency="USD",
        )
        store.upsert(opp)
        result = asyncio.run(prepare_execution(opp.dedup_key(), store, tmp_path))
        assert result["estimate"]["difficulty"] == "easy"
        ws = tmp_path / result["workspace"].split("/")[-1]
        plan = json.loads((ws / "PLAN.md").read_text())
        assert plan["estimate"]["effective_reward_usd"] == 50.0
        assert "human_approval" in plan["steps"]

    def test_record_approval_gate(self, store, tmp_path):
        import asyncio
        import json

        from cores.opportunity.live_pipeline import LiveOpportunity, prepare_execution, record_approval

        opp = LiveOpportunity(id="a1", platform="opire", adapter="a", title="Fix parser bug", url="https://x.test/i")
        store.upsert(opp)
        asyncio.run(prepare_execution(opp.dedup_key(), store, tmp_path))

        res = record_approval(opp.dedup_key(), approved=True, approved_by="adriel", store=store)
        assert res["approved"] is True
        approval = store._items[opp.dedup_key()].raw["execution"]["approval"]
        assert approval["approved"] is True and approval["approved_by"] == "adriel"
        ws = tmp_path / store._items[opp.dedup_key()].raw["execution"]["workspace"].split("/")[-1]
        assert json.loads((ws / "APPROVAL.json").read_text())["approved"] is True

        # unprepared opportunity cannot be approved
        other = LiveOpportunity(id="a2", platform="opire", adapter="a", title="x", url="u2")
        store.upsert(other)
        assert "error" in record_approval(other.dedup_key(), True, store=store)


class TestLiveConnections:
    def test_status_never_leaks_values(self, monkeypatch, tmp_path):
        import cores.opportunity.live_connections as lc

        env = tmp_path / "opportunity.env"
        env.write_text("GITHUB_TOKEN=secretvalue123\nUNKNOWN_KEY=keepme\n# comment\n")
        monkeypatch.setattr(lc, "ENV_FILE", env)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        out = lc.connection_status()
        assert "secretvalue123" not in str(out)
        gh = next(s for s in out["sources"] if s["source"] == "github_bounties")
        assert gh["state"] == "configured"
        assert gh["env_vars"] == [{"name": "GITHUB_TOKEN", "configured": True}]
        assert out["env_file_exists"] is True

    def test_set_and_revoke_roundtrip(self, monkeypatch, tmp_path):
        import cores.opportunity.live_connections as lc

        env = tmp_path / "opportunity.env"
        monkeypatch.setattr(lc, "ENV_FILE", env)
        monkeypatch.setattr(lc, "ENV_BACKUP", tmp_path / "opportunity.env.bak")
        for var in ("GITHUB_TOKEN", "ALGORA_API_KEY"):
            monkeypatch.delenv(var, raising=False)

        assert lc.set_credential("GITHUB_TOKEN", "tok123")["stored"] is True
        assert "GITHUB_TOKEN=tok123" in env.read_text()
        assert oct(env.stat().st_mode & 0o777) == "0o600"

        # unknown var rejected
        assert "error" in lc.set_credential("RANDOM_VAR", "x")

        # revoke removes it, keeps other lines
        env.write_text("GITHUB_TOKEN=tok123\n# note\nOPIRE_API_KEY=op\n")
        res = lc.revoke_credential("GITHUB_TOKEN")
        assert res["revoked"] is True
        assert "GITHUB_TOKEN" not in env.read_text()
        assert "OPIRE_API_KEY=op" in env.read_text()
        assert "# note" in env.read_text()
        assert (tmp_path / "opportunity.env.bak").exists()

    def test_revoke_process_env_refused(self, monkeypatch, tmp_path):
        import cores.opportunity.live_connections as lc

        env = tmp_path / "opportunity.env"
        monkeypatch.setattr(lc, "ENV_FILE", env)
        monkeypatch.setenv("GITHUB_TOKEN", "fromprocess")
        env.write_text("GITHUB_TOKEN=fromfile\n")
        res = lc.revoke_credential("GITHUB_TOKEN")
        assert res["revoked"] is False
        assert "process environment" in res["detail"]

    def test_placeholder_tokens_not_configured(self, monkeypatch, tmp_path):
        import cores.opportunity.live_connections as lc

        env = tmp_path / "opportunity.env"
        env.write_text("GITHUB_TOKEN=your_token_here\n")
        monkeypatch.setattr(lc, "ENV_FILE", env)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        out = lc.connection_status()
        gh = next(s for s in out["sources"] if s["source"] == "github_bounties")
        assert gh["state"] != "configured"

    def test_probe_no_impl_is_honest(self, monkeypatch, tmp_path):
        import asyncio

        import cores.opportunity.live_connections as lc

        env = tmp_path / "opportunity.env"
        env.write_text("ALGORA_API_KEY=abc\n")
        monkeypatch.setattr(lc, "ENV_FILE", env)
        monkeypatch.delenv("ALGORA_API_KEY", raising=False)
        res = asyncio.run(lc.test_connection("algora"))
        assert res["verified"] is False
        assert "no auth probe" in res["detail"]


class TestRevenueLedgerAmounts:
    def test_paid_requires_evidence(self, tmp_path):
        from core.execution_queue.models import ExecutionQueueStore
        from cores.opportunity.revenue_ledger import RevenueLedger

        ledger = RevenueLedger(ExecutionQueueStore(tmp_path / "q.json"))
        res = ledger.record_amount("i1", "paid", 100.0)
        assert "error" in res and "evidence" in res["error"]
        ok = ledger.record_amount("i1", "paid", 100.0, evidence={"tx": "0xabc"})
        assert "entry" in ok

    def test_buckets_and_verified_income(self, tmp_path):
        from core.execution_queue.models import ExecutionQueueStore
        from cores.opportunity.revenue_ledger import RevenueLedger

        ledger = RevenueLedger(ExecutionQueueStore(tmp_path / "q.json"))
        ledger.record_amount("i1", "advertised", 500.0, currency="USD")
        ledger.record_amount("i1", "expected", 300.0)
        ledger.record_amount("i1", "paid", 120.0, fees=10.0, evidence={"receipt": "r1"})
        s = ledger.get_financial_summary()
        assert s["verified_income_total_usd"] == 120.0
        assert s["by_bucket"]["advertised"]["USD"] == 500.0
        assert s["by_bucket"]["paid"]["USD"] == 120.0
        entry = ledger._store.get("i1")["payload"]["finance"]["latest"]["paid"]
        assert entry["net"] == 110.0

    def test_invalid_bucket_rejected(self, tmp_path):
        from core.execution_queue.models import ExecutionQueueStore
        from cores.opportunity.revenue_ledger import RevenueLedger

        ledger = RevenueLedger(ExecutionQueueStore(tmp_path / "q.json"))
        assert "error" in ledger.record_amount("i1", "income", 5.0)

    def test_draft_payment_inquiry_never_sends(self, store):
        from cores.opportunity.live_pipeline import LiveOpportunity, draft_payment_inquiry

        opp = LiveOpportunity(
            id="pi1",
            platform="algora",
            adapter="a",
            title="Fix bug",
            url="https://x.test",
            reward=100.0,
            currency="USD",
        )
        opp.raw["eligibility"] = {"payment_fallbacks": {"fallback": "private_message", "notes": "ask poster"}}
        store.upsert(opp)
        res = draft_payment_inquiry(opp.dedup_key(), store)
        assert "CONFIRM" in res["draft"]
        assert "100.0 USD" in res["draft"]
        assert "private_message" in res["draft"]
        assert "nothing sent" in res["note"]

    def test_clone_repo_local(self, tmp_path):
        import asyncio
        import subprocess

        from cores.opportunity.live_pipeline import _clone_repo

        src = tmp_path / "src_repo"
        src.mkdir()
        (src / "README.md").write_text("hi")
        subprocess.run(["git", "init", "-q"], cwd=src, check=True)
        subprocess.run(["git", "add", "-A"], cwd=src, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
            cwd=src,
            check=True,
        )
        dest = tmp_path / "clone"
        res = asyncio.run(_clone_repo(str(src), dest, timeout=30))
        assert res["cloned"] is True
        assert (dest / "README.md").exists()

    def test_clone_repo_failure_is_evidence(self, tmp_path):
        import asyncio

        from cores.opportunity.live_pipeline import _clone_repo

        res = asyncio.run(_clone_repo("/nonexistent/repo", tmp_path / "c2", timeout=15))
        assert res["cloned"] is False
        assert "error" in res

    def test_analyze_workspace_no_repo(self, store):
        import asyncio

        from cores.opportunity.live_pipeline import LiveOpportunity, analyze_workspace

        opp = LiveOpportunity(id="aw1", platform="opire", adapter="a", title="x", url="u")
        store.upsert(opp)
        res = asyncio.run(analyze_workspace(opp.dedup_key(), store=store))
        assert "error" in res

    def test_analyze_workspace_with_cloned_repo(self, store, tmp_path):
        import asyncio
        import subprocess

        from cores.opportunity.live_pipeline import LiveOpportunity, analyze_workspace

        # build a tiny python repo and clone it into the workspace manually
        src = tmp_path / "srcrepo"
        src.mkdir()
        (src / "pyproject.toml").write_text("[project]\nname='x'\n")
        (src / "test_x.py").write_text("def test_ok():\n    assert True\n")
        subprocess.run(["git", "init", "-q"], cwd=src, check=True)
        subprocess.run(["git", "add", "-A"], cwd=src, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "i"],
            cwd=src,
            check=True,
        )
        ws = tmp_path / "ws"
        subprocess.run(["git", "clone", "-q", "--depth", "1", str(src), str(ws / "repo")], check=True)

        opp = LiveOpportunity(id="aw2", platform="issuehunt", adapter="a", title="x", url="https://github.com/a/b/issues/1")
        opp.raw["execution"] = {"workspace": str(ws)}
        store.upsert(opp)
        res = asyncio.run(analyze_workspace(opp.dedup_key(), store=store))
        assert res["analysis"]["language"] in ("python", "unknown")
        assert (ws / "ANALYSIS.md").exists()
        assert store._items[opp.dedup_key()].raw["execution"]["analysis"]["language"] == res["analysis"]["language"]

    def test_external_status_requires_evidence(self, store):
        from cores.opportunity.live_pipeline import LiveOpportunity, record_external_status

        opp = LiveOpportunity(id="es1", platform="opire", adapter="a", title="x", url="u", status="in_progress")
        store.upsert(opp)
        assert "error" in record_external_status(opp.dedup_key(), "submitted", {}, store)
        res = record_external_status(opp.dedup_key(), "submitted", {"url": "https://opire.dev/sub/1"}, store)
        assert res["status"] == "submitted"
        assert store._items[opp.dedup_key()].status == "submitted"

    def test_external_status_validates_transitions(self, store):
        from cores.opportunity.live_pipeline import LiveOpportunity, record_external_status

        opp = LiveOpportunity(id="es2", platform="opire", adapter="a", title="x", url="u", status="discovered")
        store.upsert(opp)
        # discovered → paid is not a valid path
        res = record_external_status(opp.dedup_key(), "paid", {"tx": "1"}, store)
        assert "error" in res
        # discovered → in_progress? not in EXTERNAL_TRANSITIONS as a status arg;
        # external statuses only
        res = record_external_status(opp.dedup_key(), "bogus", {"x": 1}, store)
        assert "error" in res

    def test_paid_mirrors_to_ledger(self, store, tmp_path, monkeypatch):
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        from cores.opportunity.live_pipeline import LiveOpportunity, record_external_status

        opp = LiveOpportunity(
            id="es3",
            platform="algora",
            adapter="a",
            title="x",
            url="u",
            status="accepted",
            reward=75.0,
            currency="USD",
        )
        store.upsert(opp)
        res = record_external_status(
            opp.dedup_key(),
            "paid",
            {"tx": "0xdead", "paid_at": "2026-11-10", "payout_method": "usdc"},
            store,
        )
        assert res["status"] == "paid"
        assert res["ledger"] == "recorded"


class TestRevenueFirstScoring:
    """REVENUE_FIRST_ENGINEERING.md §3 — viability over advertised reward."""

    def _elig(self, **overrides: Any) -> dict[str, Any]:
        base = {
            "opportunity_id": "x",
            "platform": "algora",
            "argentina_compatible": "unknown",
            "payment_method": "unknown",
            "requires_account": "unknown",
            "requires_interview": "unknown",
            "requires_experience": "unknown",
            "requires_portfolio": "unknown",
            "requires_assessment": "unknown",
            "blockers": [],
            "evidence": "test",
        }
        base.update(overrides)
        return base

    def _estimate(self, reward: float, hours: float = 4.0) -> dict[str, Any]:
        return {
            "effective_reward_usd": reward,
            "estimated_effort_hours": hours,
            "difficulty": "medium",
        }

    def _opp(self, reward: float = 50.0) -> LiveOpportunity:
        return LiveOpportunity(id="r1", platform="algora", adapter="a", title="t", url="u", reward=reward)

    def test_accessible_small_beats_blocked_large(self):
        from cores.opportunity.live_pipeline import score_opportunity

        accessible = score_opportunity(
            self._opp(40.0),
            eligibility=self._elig(
                argentina_compatible="yes",
                payment_method="platform_supported",
                requires_account="no",
                requires_interview="no",
                requires_experience="no",
                requires_portfolio="no",
                requires_assessment="no",
            ),
            estimate=self._estimate(40.0, 2.0),
        )
        blocked = score_opportunity(
            self._opp(500.0),
            eligibility=self._elig(
                argentina_compatible="no",
                payment_method="unknown",
                requires_account="yes",
                requires_interview="yes",
                requires_experience="yes",
                requires_portfolio="yes",
                requires_assessment="yes",
            ),
            estimate=self._estimate(500.0, 12.0),
        )
        assert accessible["score"] > blocked["score"]

    def test_confidence_reflects_unknown_dimensions(self):
        from cores.opportunity.live_pipeline import score_opportunity

        definitive = score_opportunity(
            self._opp(),
            eligibility=self._elig(
                argentina_compatible="yes",
                payment_method="platform_supported",
                requires_account="no",
                requires_interview="no",
                requires_experience="no",
                requires_portfolio="no",
                requires_assessment="no",
            ),
            estimate=self._estimate(50.0),
        )
        unknown = score_opportunity(self._opp(), eligibility=self._elig(), estimate=self._estimate(50.0))
        assert definitive["confidence"] == 1.0
        assert unknown["confidence"] < definitive["confidence"]

    def test_reward_per_hour_in_metrics(self):
        from cores.opportunity.live_pipeline import score_opportunity

        s = score_opportunity(
            self._opp(100.0),
            eligibility=self._elig(argentina_compatible="yes", payment_method="fallback_available"),
            estimate=self._estimate(100.0, 2.0),
        )
        assert s["estimated_net_per_hour_usd"] == 48.5  # (100 - 2h*$1.50) / 2h
        assert s["estimated_gross_per_hour_usd"] == 50.0
        assert "note" in s and "not confirmed income" in s["note"]

    def test_rank_excludes_terminal_and_sorts(self, store):
        from cores.opportunity.live_pipeline import rank_opportunities

        store.upsert(LiveOpportunity(id="big", platform="algora", adapter="a", title="t", url="u", reward=300.0))
        store.upsert(LiveOpportunity(id="small", platform="algora", adapter="a", title="t", url="u", reward=10.0))
        store.upsert(LiveOpportunity(id="dead", platform="algora", adapter="a", title="t", url="u", reward=999.0, status="expired"))
        result = rank_opportunities(store=store)
        keys = [r["opportunity_id"] for r in result["ranked"]]
        assert "algora:dead" not in keys
        assert keys[0] == "algora:big"
        assert result["total_evaluated"] == 2

    def test_rank_min_score_filter(self, store):
        from cores.opportunity.live_pipeline import rank_opportunities

        store.upsert(LiveOpportunity(id="x", platform="algora", adapter="a", title="t", url="u", reward=0.0))
        result = rank_opportunities(store=store, min_score=999.0)
        assert result["ranked"] == []

    def test_paid_amount_source_flags_advertised_fallback(self, store, tmp_path, monkeypatch):
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        from cores.opportunity.live_pipeline import LiveOpportunity, record_external_status

        store.upsert(
            LiveOpportunity(
                id="amt1",
                platform="algora",
                adapter="a",
                title="t",
                url="u",
                reward=75.0,
                status="accepted",
            )
        )
        res = record_external_status("algora:amt1", "paid", {"url": "https://pay.example/rcpt/1"}, store=store)
        assert res["amount_source"] == "advertised_fallback"

        store.upsert(
            LiveOpportunity(
                id="amt2",
                platform="algora",
                adapter="a",
                title="t",
                url="u",
                reward=75.0,
                status="accepted",
            )
        )
        res2 = record_external_status("algora:amt2", "paid", {"receipt": "r2"}, store=store, amount=68.5, currency="USD")
        assert res2["amount_source"] == "explicit"

        store.upsert(
            LiveOpportunity(
                id="amt3",
                platform="algora",
                adapter="a",
                title="t",
                url="u",
                reward=75.0,
                status="accepted",
            )
        )
        res3 = record_external_status("algora:amt3", "paid", {"receipt": "r3", "amount": 70.0}, store=store)
        assert res3["amount_source"] == "explicit"


class _FakeLedger:
    """Minimal stand-in for RevenueLedger exposing _store._items."""

    def __init__(self, items: dict[str, Any]):
        self._store = SimpleNamespace(_items=items)


def _ledger_item(advertised_at: str | None = None, paid_at: str | None = None) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    if advertised_at:
        latest["advertised"] = {"amount": 50.0, "recorded_at": advertised_at}
    if paid_at:
        latest["paid"] = {"amount": 50.0, "recorded_at": paid_at, "evidence": {"url": "x"}}
    return {"payload": {"finance": {"latest": latest}}}


class TestPlatformTrackRecord:
    def test_no_data(self):
        tr = platform_track_record("algora", ledger=_FakeLedger({}))
        assert tr["data_status"] == "no_payouts_yet"
        assert tr["reward_realization_rate"] is None
        assert tr["time_to_first_payout_days"] is None

    def test_advertised_only_means_zero_rate(self):
        items = {"live:algora:a1": _ledger_item(advertised_at="2026-11-01T00:00:00+00:00")}
        tr = platform_track_record("algora", ledger=_FakeLedger(items))
        assert tr["advertised_items"] == 1
        assert tr["reward_realization_rate"] == 0.0
        assert tr["data_status"] == "no_payouts_yet"

    def test_paid_computes_rate_and_ttfp(self):
        items = {
            "live:algora:a1": _ledger_item(
                advertised_at="2026-11-01T00:00:00+00:00",
                paid_at="2026-11-11T00:00:00+00:00",
            ),
            "live:algora:a2": _ledger_item(advertised_at="2026-11-02T00:00:00+00:00"),
            "live:other:b1": _ledger_item(paid_at="2026-11-05T00:00:00+00:00"),
        }
        tr = platform_track_record("algora", ledger=_FakeLedger(items))
        assert tr["advertised_items"] == 2
        assert tr["paid_items"] == 1
        assert tr["reward_realization_rate"] == 0.5
        assert tr["time_to_first_payout_days"] == 10.0
        assert tr["data_status"] == "ok"

    def test_score_includes_track_record(self):
        opp = _to_live("algora", _raw())
        assert opp is not None
        s = score_opportunity(opp)
        assert "track_record" in s
        assert "platform_history" in s["breakdown"]
        assert s["track_record"]["platform"] == "algora"
        assert 0.0 <= s["score"] <= 100.0


class TestAiCostScoring:
    def test_score_reports_ai_cost_and_net(self):
        opp = _to_live("algora", _raw(reward=100.0, effort_hours=4.0))
        assert opp is not None
        s = score_opportunity(opp)
        assert s["estimated_ai_cost_usd"] == 6.0  # 4h * $1.50 default
        assert s["estimated_net_reward_usd"] == 94.0
        assert s["estimated_net_per_hour_usd"] == 23.5
        assert s["estimated_gross_per_hour_usd"] == 25.0

    def test_unprofitable_after_ai_cost_scores_low_effort(self):
        # $10 reward, 8h effort -> net negative -> lowest effort tier
        opp = _to_live("algora", _raw(reward=10.0))
        assert opp is not None
        s = score_opportunity(
            opp,
            estimate={"effective_reward_usd": 10.0, "estimated_effort_hours": 8.0},
        )
        assert s["estimated_net_reward_usd"] < 0
        assert s["breakdown"]["reward_per_hour_fit"] == 3.0


class TestFundingState:
    def test_badge_detected_not_authorized(self):
        from cores.opportunity.live_pipeline import assess_funding_state

        opp = _to_live("issuehunt", _raw(reward=60.0))
        assert opp is not None
        f = assess_funding_state(opp)
        assert f["funding_state"] == "FUNDING_BADGE_DETECTED"
        assert f["execution_authorized"] is False
        assert f["payout_route_verified"] is False

    def test_score_includes_funding(self):
        opp = _to_live("issuehunt", _raw(reward=60.0))
        assert opp is not None
        s = score_opportunity(opp)
        assert s["funding"]["funding_state"] == "FUNDING_BADGE_DETECTED"


class TestIssueFreshness:
    def test_old_issue_penalized(self):
        opp = _to_live("issuehunt", _raw(reward=100.0))
        assert opp is not None
        from datetime import UTC, datetime, timedelta

        recent = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        fresh = score_opportunity(
            opp,
            estimate={"effective_reward_usd": 100.0, "estimated_effort_hours": 2.0, "created_at": recent},
        )
        stale = score_opportunity(
            opp,
            estimate={"effective_reward_usd": 100.0, "estimated_effort_hours": 2.0, "created_at": "2017-03-11T00:00:00+00:00"},
        )
        assert fresh["breakdown"]["issue_freshness"] == 1.0
        assert stale["breakdown"]["issue_freshness"] == 0.5
        assert stale["score"] < fresh["score"]
        assert stale["breakdown"]["issue_age_days"] > 3000
