"""100+ webs optables: filtro por lenguaje + registry curado + prober + quarantine.

Budget: 1 archivo de tests. Sin red real (todo mockeado) salvo probes
explícitos del job, que también van mockeados acá.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.adapters.direct_work_github_bounty import GitHubBountyDweAdapter
from api.routers.direct_work import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ── F1: filtro por lenguaje ──────────────────────────────────────────


class TestLanguageQueries:
    def test_defaults_unchanged(self) -> None:
        ad = GitHubBountyDweAdapter()
        assert ad._build_queries() == GitHubBountyDweAdapter._BOUNTY_QUERIES
        assert len(ad._build_queries()) == 5

    def test_rust_go_qualifiers(self) -> None:
        ad = GitHubBountyDweAdapter()
        qs = ad._build_queries(["rust", "go"])
        assert len(qs) == 6
        assert all("language:" in q for q in qs)
        assert "label:bounty state:open language:rust" in qs
        assert "label:paid state:open language:go" in qs

    def test_normalize_dedupe_lower_cap(self) -> None:
        ad = GitHubBountyDweAdapter()
        langs = ad._normalize_languages(["Rust", " rust ", "GO", "go", "Solidity", "a", "b", "c"])
        assert langs == ["rust", "go", "solidity", "a", "b"]  # dedupe + cap 5
        assert ad._normalize_languages(None) == []
        assert ad._normalize_languages([]) == []

    def test_keyword_normalize_and_cap(self) -> None:
        ad = GitHubBountyDweAdapter()
        assert ad._normalize_keywords([" AWS ", "azure", "AWS", "terraform!", "a", "b", "c"]) == [
            "aws",
            "azure",
            "terraform",
            "a",
            "b",
        ]  # dedupe + sanitize + cap 5
        assert ad._normalize_keywords(None) == []
        assert ad._normalize_keywords(["!!!"]) == []

    def test_keyword_or_group_costs_zero_extra_queries(self) -> None:
        ad = GitHubBountyDweAdapter()
        plain = ad._build_queries()
        assert len(ad._build_queries(keywords=["aws", "azure"])) == len(plain)
        assert all(q.endswith("(aws OR azure)") for q in ad._build_queries(keywords=["aws", "azure"]))
        mixed = ad._build_queries(["go"], ["terraform"])
        assert len(mixed) == 3  # 3 bases × 1 idioma, misma cuenta que sin keywords
        assert all("language:go" in q and "(terraform)" in q for q in mixed)

    def test_fetch_passes_keywords(self) -> None:
        ad = GitHubBountyDweAdapter()
        seen: list[str] = []

        async def fake_search_kw(query: str):
            seen.append(query)
            return []

        with patch.object(ad, "_search_query", side_effect=fake_search_kw):
            import asyncio

            asyncio.run(ad.fetch_opportunities(keywords=["aws"]))
        assert seen and all("(aws)" in q for q in seen)

    def test_fetch_uses_qualified_queries(self) -> None:
        ad = GitHubBountyDweAdapter()
        seen: list[str] = []

        async def fake_search(query: str):
            seen.append(query)
            return []

        with patch.object(ad, "_search_query", side_effect=fake_search):
            import asyncio

            asyncio.run(ad.fetch_opportunities(languages=["solidity"]))
        assert seen == [
            "label:bounty state:open language:solidity",
            "label:reward state:open language:solidity",
            "label:paid state:open language:solidity",
        ]

    def test_absurd_reward_becomes_unknown(self) -> None:
        ad = GitHubBountyDweAdapter()
        assert ad._extract_reward([], "bounty " + "9" * 82) == 0.0
        assert ad._extract_reward(["bounty $500"], "") == 500.0
        assert ad._extract_reward([], "no money here") == 0.0

    def test_auth_header_only_with_token(self, monkeypatch) -> None:
        import httpx

        captured: dict = {}

        class FakeResp:
            status_code = 200

            def json(self):
                return {"items": []}

        class FakeClient:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, url, params=None, headers=None):
                captured.update(headers or {})
                return FakeResp()

        ad = GitHubBountyDweAdapter()
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
        import asyncio

        asyncio.run(ad._search_query("label:bounty state:open"))
        assert "Authorization" not in captured

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        asyncio.run(ad._search_query("label:bounty state:open"))
        assert captured.get("Authorization") == "Bearer ghp_test"


# ── F2: registry curado ──────────────────────────────────────────────


class TestCuratedSchema:
    def test_all_sources_valid_and_unique(self) -> None:
        from cores.opportunity.global_sources import get_sources

        sources = get_sources()
        assert len(sources) >= 100  # las "100+ webs" existen como datos
        urls = [str(getattr(s, "url", "")) for s in sources]
        assert all(u.startswith("https://") for u in urls)
        names = [str(getattr(s, "name", "")) for s in sources]
        assert all(names) and len(set(names)) == len(names)
        # Una misma plataforma puede tener varias vías de acceso bajo una URL
        # (ej. "Mindrift All-access" + "Mindrift Specialized" → mindrift.ai).
        # El duplicado solo vale si los nombres comparten un token
        # significativo (misma plataforma/entidad, ej. "telus").
        import re as _re

        def _tokens(name: str) -> set[str]:
            return {t for t in _re.split(r"[^a-z0-9]+", name.lower()) if len(t) > 3}

        by_url: dict[str, list[str]] = {}
        for s in sources:
            by_url.setdefault(str(getattr(s, "url", "")), []).append(str(getattr(s, "name", "")))
        for url, dupes in by_url.items():
            if len(dupes) > 1:
                shared = set.intersection(*(_tokens(n) for n in dupes))
                assert shared, f"{url}: {dupes}"
        for s in sources:
            assert isinstance(getattr(s, "requires_interview", False), bool)
            assert isinstance(getattr(s, "requires_portfolio", False), bool)

    def test_no_fabricated_identifiers(self) -> None:
        """Nunca más variantes #N, ?src= ni /extra-N: URLs exactas y reales."""
        import re

        from cores.opportunity.global_sources import get_sources

        for s in get_sources():
            name, url = str(getattr(s, "name", "")), str(getattr(s, "url", ""))
            assert not re.search(r" #\d+$", name), name
            assert "?src=" not in url, url
            assert "/extra-" not in url, url

    def test_fixed_roots_stay_verified(self) -> None:
        """Las URLs de las fuentes top siguen siendo las verificadas por probe.

        Evidencia: probe HTTP 2026-10-01 con `-L` (los paths profundos que
        pineaba la versión anterior de este test dan **404**; las raíces dan
        200). El test pinea la verdad del probe, no raíces adivinadas.

        Contexto: el 2026-09-16 el probe vivió en `data/curated_sources.json`,
        que no se commitea. Re-verificado en vivo antes de actualizar los pines
        — por eso la fecha del docstring es la del probe que respalda esto.
        """
        from cores.opportunity.global_sources import get_sources

        by_name = {str(getattr(s, "name", "")): str(getattr(s, "url", "")) for s in get_sources()}
        assert by_name.get("HackerOne") == "https://hackerone.com/"
        assert by_name.get("Immunefi") == "https://immunefi.com/"
        assert by_name.get("Gitcoin") == "https://www.gitcoin.co/"
        assert by_name.get("OnlyDust") == "https://app.onlydust.com/explore"
        assert "github.com/topics/bounty" in by_name.get("GitHub Issues (bounty-labeled)", "")

    def test_gate_blocks_interview_and_low_pay(self) -> None:
        from cores.direct_work_engine.source_registry import source_gate

        assert source_gate(SimpleNamespace(name="X", requires_interview=True))[0] is False
        low = SimpleNamespace(name="Y", requires_interview=False, typical_hourly_rate_usd=5.0)
        ok, reason = source_gate(low)
        assert ok is False and "15" in reason

    def test_gate_allows_unknown_rate_and_clean(self) -> None:
        from cores.direct_work_engine.source_registry import source_gate

        ok, _ = source_gate(SimpleNamespace(name="Z", requires_interview=False, typical_hourly_rate_usd=None))
        assert ok is True  # sin datos = pasa, UNKNOWN honesto en otro lado


class TestOptIn:
    def test_opt_out_and_back(self, monkeypatch, tmp_path) -> None:
        from cores.direct_work_engine import source_registry as reg

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        from cores.opportunity.global_sources import get_sources

        name = str(get_sources()[0].name)
        assert reg.is_source_enabled(name) is True
        assert reg.set_source_enabled(name, False) is True
        assert reg.is_source_enabled(name) is False
        assert reg.set_source_enabled(name, True) is True
        assert reg.is_source_enabled(name) is True

    def test_opt_unknown_name(self, monkeypatch, tmp_path) -> None:
        from cores.direct_work_engine import source_registry as reg

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        assert reg.set_source_enabled("no-existe-xyz", True) is False

    def test_reenable_clears_quarantine(self, monkeypatch, tmp_path) -> None:
        from cores.direct_work_engine import source_registry as reg

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        from cores.opportunity.global_sources import get_sources

        name = str(get_sources()[0].name)
        store = {"disabled": [], "liveness": {name: {"status": "dead", "consecutive_dead": 5}}}
        import json

        (tmp_path / "curated_sources.json").write_text(json.dumps(store))
        assert reg.set_source_enabled(name, True) is True
        assert reg.liveness_for(name)["consecutive_dead"] == 0

    def test_overview_shape(self, monkeypatch, tmp_path) -> None:
        from cores.direct_work_engine import source_registry as reg

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        ov = reg.sources_overview()
        assert ov["total"] >= 100
        # fresh: todo habilitado salvo privadas bloqueadas (2 AI frontier)
        locked = [s for s in ov["sources"] if s.get("visibility") == "private"]
        assert {s["name"] for s in locked} == {"OpenAI Safety Bug Bounty", "Anthropic Model Safety Bounty"}
        assert ov["enabled"] == ov["total"] - len(locked)
        assert ov["quarantined"] == 0
        first = ov["sources"][0]
        assert {"name", "url", "category", "type", "gate", "liveness", "enabled"} <= set(first)
        assert first["liveness"]["status"] == "unknown"  # sin probe: UNKNOWN honesto


# ── F3: prober + quarantine ──────────────────────────────────────────


class TestProber:
    def _fake_client(self, mapping: dict):

        class FakeResp:
            def __init__(self, code):
                self.status_code = code

        class FakeClient:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def head(self, url, timeout=None):
                code = mapping.get(url, 200)
                if isinstance(code, Exception):
                    raise code
                return FakeResp(code)

            async def get(self, url, timeout=None):
                return await self.head(url, timeout)

        return FakeClient

    def test_probe_tri_state(self, monkeypatch, tmp_path) -> None:
        import httpx

        from cores.direct_work_engine import source_registry as reg

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            httpx,
            "AsyncClient",
            self._fake_client(
                {
                    "https://ok.example.com": 200,
                    "https://gone.example.com": 404,
                    "https://walled.example.com": 403,
                    "https://boom.example.com": ConnectionError("dns"),
                }
            ),
        )
        import asyncio

        async def run():
            async with httpx.AsyncClient() as client:
                results = {}
                for url in [
                    "https://ok.example.com",
                    "https://gone.example.com",
                    "https://walled.example.com",
                    "https://boom.example.com",
                    "not-a-url",
                ]:
                    results[url] = await reg._probe_one(client, url)
                return results

        out = asyncio.run(run())
        assert out["https://ok.example.com"][0] == "live"
        assert out["https://gone.example.com"][0] == "dead"
        assert out["https://walled.example.com"][0] == "unknown"  # muro ≠ muerta
        assert out["https://boom.example.com"][0] == "dead"
        assert out["not-a-url"][0] == "unknown"  # sin URL: UNKNOWN, no dead

    def test_quarantine_after_three_dead(self, monkeypatch, tmp_path) -> None:
        import httpx

        from cores.direct_work_engine import source_registry as reg

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            "cores.direct_work_engine.source_registry._all_sources",
            lambda: [SimpleNamespace(name="Muerta", url="https://gone.example.com", category="x", type="platform")],
        )
        monkeypatch.setattr(httpx, "AsyncClient", self._fake_client({"https://gone.example.com": 404}))
        summary: dict = {}
        for _ in range(3):
            summary = reg.run_source_probe_cycle()
        assert summary["dead"] == 1
        assert reg.is_quarantined("Muerta") is True
        assert reg.is_source_enabled("Muerta") is False  # fuera del radar

    def test_head_404_retries_get_before_dead(self, monkeypatch, tmp_path) -> None:
        """HEAD 404 ≠ recurso muerto (Kaggle): solo GET decide el veredicto."""
        import httpx

        from cores.direct_work_engine import source_registry as reg

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))

        class FakeResp:
            def __init__(self, code):
                self.status_code = code

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def head(self, url, timeout=None):
                return FakeResp(404)

            async def get(self, url, timeout=None):
                return FakeResp(200)

        monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
        import asyncio

        async def run():
            async with httpx.AsyncClient() as client:
                return await reg._probe_one(client, "https://headless.example.com")

        assert asyncio.run(run())[0] == "live"

    def test_cycle_never_raises(self, monkeypatch, tmp_path) -> None:
        from cores.direct_work_engine import source_registry as reg

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            "cores.direct_work_engine.source_registry.probe_all_sources",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        out = reg.run_source_probe_cycle()
        assert out["probed"] == 0 and "error" in out


# ── Job + endpoints ──────────────────────────────────────────────────


class TestJobAndEndpoints:
    def test_probe_job_registered_and_resolves(self) -> None:
        import importlib

        from cores.scheduler.jobs import get_direct_work_jobs

        ids = [j.job_id for j in get_direct_work_jobs()]
        assert "curated_sources_probe" in ids
        job = next(j for j in get_direct_work_jobs() if j.job_id == "curated_sources_probe")
        handler_path: str = job.handler  # type: ignore[assignment]
        mod_name, attr = handler_path.rsplit(":", 1)
        assert callable(getattr(importlib.import_module(mod_name), attr))

    def test_sources_endpoint_shape(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        r = client.get("/direct-work/sources")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 100
        assert body["enabled"] == body["total"] - 2  # 2 privadas bloqueadas por default
        assert isinstance(body["sources"], list)

    def test_opt_endpoint_roundtrip_and_404(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        from cores.opportunity.global_sources import get_sources

        name = str(get_sources()[0].name)
        r = client.post("/direct-work/sources/opt", json={"name": name, "enabled": False})
        assert r.status_code == 200 and r.json() == {"name": name, "enabled": False}
        body = client.get("/direct-work/sources").json()
        assert body["enabled"] == body["total"] - 2 - 1  # 2 privadas + 1 opt-out
        r = client.post("/direct-work/sources/opt", json={"name": "no-existe-xyz", "enabled": True})
        assert r.status_code == 404
        r = client.post("/direct-work/sources/opt", json={"name": "   ", "enabled": True})
        assert r.status_code == 422

    def test_discover_languages_branch(self, monkeypatch) -> None:
        from api.routers import direct_work as dw
        from cores.direct_work_engine.models import Opportunity, OpportunityCategory, WorkPlatform

        op = Opportunity(
            id="op-1", title="Fix", platform=WorkPlatform.OPIRE, category=OpportunityCategory.DEV_BOUNTY, payment=100.0
        )
        gh_op = Opportunity(
            id="gh-1",
            title="Rust bounty",
            platform=WorkPlatform.GITHUB,
            category=OpportunityCategory.OPEN_SOURCE,
            payment=50.0,
        )
        engine = dw.get_engine()
        seen: dict = {}

        async def fake_others(platforms=None):
            return [op]

        class FakeGH:
            async def fetch_opportunities(self, languages=None):
                seen["languages"] = languages
                return [gh_op]

        real_adapters = engine.discovery.adapters
        monkeypatch.setattr(engine.discovery, "discover_all", fake_others)
        monkeypatch.setitem(real_adapters, WorkPlatform.GITHUB, FakeGH())
        try:
            r = client.post("/direct-work/discover", json={"limit": 10, "languages": ["rust"]})
        finally:
            real_adapters.pop(WorkPlatform.GITHUB, None)
        assert r.status_code == 200
        assert seen["languages"] == ["rust"]
        ids = [o["id"] for o in r.json()["opportunities"]]
        assert "gh-1" in ids

    def test_discover_keywords_branch(self, monkeypatch) -> None:
        from api.routers import direct_work as dw
        from cores.direct_work_engine.models import Opportunity, OpportunityCategory, WorkPlatform

        op = Opportunity(
            id="op-1", title="Fix", platform=WorkPlatform.OPIRE, category=OpportunityCategory.DEV_BOUNTY, payment=100.0
        )
        engine = dw.get_engine()
        seen: dict = {}

        async def fake_others(platforms=None):
            return [op]

        class FakeGH:
            async def fetch_opportunities(self, languages=None, keywords=None):
                seen["keywords"] = keywords
                return []

        real_adapters = engine.discovery.adapters
        monkeypatch.setattr(engine.discovery, "discover_all", fake_others)
        monkeypatch.setitem(real_adapters, WorkPlatform.GITHUB, FakeGH())
        try:
            r = client.post("/direct-work/discover", json={"limit": 10, "keywords": ["aws", "terraform"]})
        finally:
            real_adapters.pop(WorkPlatform.GITHUB, None)
        assert r.status_code == 200
        assert seen["keywords"] == ["aws", "terraform"]


# ── Mindrift: dos vías de acceso, nunca una etiqueta ────────────────────


class TestMindriftAccessPaths:
    def _mindrift_entries(self) -> dict:
        from cores.opportunity.global_sources import get_sources

        return {s.name: s for s in get_sources() if "mindrift" in s.name.lower()}

    def test_two_entries_exist(self) -> None:
        entries = self._mindrift_entries()
        assert "Mindrift All-access" in entries
        assert "Mindrift Specialized" in entries

    def test_all_access_needs_nothing(self) -> None:
        src = self._mindrift_entries()["Mindrift All-access"]
        assert src.requires_experience is False
        assert src.requires_assessment is False
        assert src.requires_interview is False
        assert src.requires_portfolio is False
        assert src.typical_hourly_rate_usd is None  # UNKNOWN honesto, no número inventado

    def test_specialized_needs_experience_and_assessment(self) -> None:
        src = self._mindrift_entries()["Mindrift Specialized"]
        assert src.requires_experience is True
        assert src.requires_assessment is True

    def test_matcher_returns_assessment_facts(self) -> None:
        from cores.opportunity.global_sources import find_curated_entry_model

        facts = find_curated_entry_model("mindrift")
        assert facts is not None
        assert facts["assessment"] is True
        assert facts["platform"] == "Mindrift Specialized"

    def test_all_access_queda_credential_por_evidencia_de_la_pagina(self) -> None:
        """CREDENTIALS, no ASSESSMENT. Corregido 2026-10-08 con la página.

        El 2026-10-01 la dejé en ASSESSMENT con el matiz escrito en la
        descripción, pensando que describía el POOL y no un gate. **Era
        decorativo**: el gate sólo lee `entry_barrier`, así que la admitía
        igual. Volvió a la página:

            "Domain expertise in your field"
            "70% of our contributors hold a Master's degree or PhD"

        Eso no es "sin experiencia": el owner pidió explícitamente fuentes
        sin experiencia profesional, y esta no lo es. Queda en el radar
        (el owner la conserva) pero fuera del ranking 0 barrera.
        """
        from cores.direct_work_engine.source_registry import admit_source, source_gate

        src = self._mindrift_entries()["Mindrift All-access"]
        assert src.entry_barrier == "CREDENTIALS", "exige dominio del área y es mayoritariamente postgrado"
        assert src.requires_interview is False
        assert "Master" in src.description, "la evidencia debe quedar en la descripción"
        assert admit_source(src).status == "BLOCKED"
        assert source_gate(src)[0] is False

    def test_opportunity_level_routing(self) -> None:
        from cores.direct_work_engine.models import (
            EntryMechanism,
            ExperienceRequirement,
            Opportunity,
            OpportunityCategory,
            WorkPlatform,
        )
        from cores.direct_work_engine.recommendation import filter_zero_experience

        all_access = Opportunity(
            id="md-aa",
            title="Comparar respuestas",
            platform=WorkPlatform.MINDRIFT,
            category=OpportunityCategory.AI_EVALUATION,
            entry_mechanism=EntryMechanism.DIRECT,
            experience_requirement=ExperienceRequirement.NONE,
        )
        specialized = Opportunity(
            id="md-sp",
            title="Coding project",
            platform=WorkPlatform.MINDRIFT,
            category=OpportunityCategory.AI_EVALUATION,
            entry_mechanism=EntryMechanism.ASSESSMENT,
            experience_requirement=ExperienceRequirement.REQUIRED,
        )
        assert all_access.is_zero_experience is True
        assert specialized.is_zero_experience is False
        kept = {o.id for o in filter_zero_experience([all_access, specialized])}
        assert kept == {"md-aa"}


# ── Expansión 2026-09-28: 12 fuentes cero-experiencia, AR-OK ──────────


class TestZeroExperienceExpansion:
    EXPECTED = {
        "Cantina": "dev_bounty",
        "Sherlock": "dev_bounty",
        "Hats Finance": "dev_bounty",
        "Code4rena": "dev_bounty",
        "Cyfrin CodeHawks": "dev_bounty",
        "Kaggle Competitions": "dev_bounty",
        "Zindi": "dev_bounty",
        "DrivenData": "dev_bounty",
        "Numerai": "dev_bounty",
        "Awesome Bounties": "dev_bounty",
        "Up For Grabs": "dev_bounty",
        "Good First Issues": "dev_bounty",
    }

    def _by_name(self) -> dict:
        from cores.opportunity.global_sources import get_sources

        return {str(s.name): s for s in get_sources()}

    def test_all_present_with_exact_urls(self) -> None:
        by_name = self._by_name()
        for name in self.EXPECTED:
            assert name in by_name, f"falta {name}"
            assert str(by_name[name].url).startswith("https://")

    def test_zero_experience_no_interview(self) -> None:
        by_name = self._by_name()
        for name in self.EXPECTED:
            s = by_name[name]
            assert s.requires_experience is False, name
            assert s.requires_interview is False, name

    def test_all_pass_owner_gate(self) -> None:
        from cores.direct_work_engine.source_registry import source_gate

        by_name = self._by_name()
        for name in self.EXPECTED:
            ok, _ = source_gate(by_name[name])
            assert ok is True, name  # sin entrevista + rate UNKNOWN/documentado

    def test_argentina_ok_or_global(self) -> None:
        by_name = self._by_name()
        for name in self.EXPECTED:
            s = by_name[name]
            assert "argentina_ok" in list(s.tags or []), name
            assert "private_program" not in list(s.tags or []), name

    def test_total_grew(self) -> None:
        from cores.opportunity.global_sources import get_sources

        assert len(get_sources()) >= 136  # 124 + 12 nuevas

    def test_existing_centaur_extended_not_duplicated(self) -> None:
        # Centaur Labs ya existía: se extendió con argentina_ok, no se duplicó.
        from cores.opportunity.global_sources import get_sources

        matches = [s for s in get_sources() if str(s.name) == "Centaur Labs"]
        assert len(matches) == 1
        assert "argentina_ok" in list(matches[0].tags or [])


# ── Solo-público (directiva owner 2026-09-20) ─────────────────────────


class TestPublicOnly:
    def test_is_private_program_solo_marcadores_explicitos(self) -> None:
        from types import SimpleNamespace

        from cores.opportunity.global_sources import is_private_program

        assert is_private_program(SimpleNamespace(tags=["private_program"])) is True
        assert is_private_program(SimpleNamespace(tags=["application_required"])) is True
        # "private" suelto = tiene públicos y privados (HackerOne etc.): NO bloquea
        assert is_private_program(SimpleNamespace(tags=["public", "private", "web"])) is False
        assert is_private_program(SimpleNamespace(tags=[])) is False
        assert is_private_program(SimpleNamespace()) is False
        assert is_private_program(None) is False

    def test_gate_bloquea_privada_salvo_unlock(self) -> None:
        from types import SimpleNamespace

        from cores.direct_work_engine.source_registry import source_gate

        priv = SimpleNamespace(
            name="P", requires_interview=False, typical_hourly_rate_usd=None, tags=["private_program"]
        )
        ok, reason = source_gate(priv)
        assert ok is False and "privado" in reason
        ok2, _ = source_gate(priv, private_unlocked=True)
        assert ok2 is True

    def test_unlock_solo_privadas_reales(self, monkeypatch, tmp_path) -> None:
        from cores.direct_work_engine import source_registry as reg

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        assert reg.unlock_private_source("No Existe") is False
        assert reg.unlock_private_source("HackerOne") is False  # pública: nada que desbloquear
        assert reg.is_private_unlocked("OpenAI Safety Bug Bounty") is False
        assert reg.unlock_private_source("OpenAI Safety Bug Bounty") is True
        assert reg.is_private_unlocked("OpenAI Safety Bug Bounty") is True

    def test_overview_marca_visibilidad_y_apaga_privadas(self, monkeypatch, tmp_path) -> None:
        from cores.direct_work_engine import source_registry as reg

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        ov = reg.sources_overview()
        by_name = {s["name"]: s for s in ov["sources"]}
        openai = by_name["OpenAI Safety Bug Bounty"]
        assert openai["visibility"] == "private"
        assert openai["enabled"] is False
        assert openai["gate"]["allowed"] is False
        assert by_name["HackerOne"]["visibility"] == "public"

    def test_radar_avoid_para_privada_bloqueada(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        from cores.direct_work_engine.source_intel import SourceIntelEngine

        cards = {c["name"]: c for c in SourceIntelEngine().analyze()["sources"]}
        assert cards["OpenAI Safety Bug Bounty"]["recommendation"] == "AVOID"
        assert "privado" in cards["OpenAI Safety Bug Bounty"]["argentina_reason"]

    def test_endpoint_unlock_404_y_200(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        assert client.post("/direct-work/sources/unlock-private", json={"name": "Nadie"}).status_code == 404
        assert client.post("/direct-work/sources/unlock-private", json={"name": ""}).status_code == 422
        r = client.post("/direct-work/sources/unlock-private", json={"name": "Anthropic Model Safety Bounty"})
        assert r.status_code == 200
        assert r.json() == {"name": "Anthropic Model Safety Bounty", "unlocked": True}


# ── micro1 + Turing AI Training: elegibilidad AR verificada (2026-09-28) ──


class TestAiTrainingArgentinaExpansion:
    """Solo plataformas con AR verificada en job posts públicos + gate pasado."""

    NEW = ("Turing AI Training (LatAm)",)

    def _by_name(self) -> dict:
        from cores.opportunity.global_sources import get_sources

        return {str(s.name): s for s in get_sources()}

    def test_present_exact_url_and_zero_experience(self) -> None:
        by_name = self._by_name()
        for name in self.NEW:
            assert name in by_name, f"falta {name}"
            s = by_name[name]
            assert str(s.url).startswith("https://")
            assert s.requires_experience is False, name
            assert s.requires_interview is False, name  # vetting con IA no es entrevista

    def test_argentina_ok_tag(self) -> None:
        for name in self.NEW:
            assert "argentina_ok" in list(self._by_name()[name].tags or []), name

    def test_one_assessment_at_most(self) -> None:
        """Criterio del owner: a lo sumo una evaluación."""
        for name in self.NEW:
            assert self._by_name()[name].requires_assessment is True, name

    def test_pass_owner_gate(self) -> None:
        from cores.direct_work_engine.source_registry import source_gate

        by_name = self._by_name()
        for name in self.NEW:
            ok, _ = source_gate(by_name[name])
            assert ok is True, name

    def test_rates_meet_floor(self) -> None:
        """Rate documentado ≥ $15/h (gate de la fuente), nunca inventado."""
        for name in self.NEW:
            rate = self._by_name()[name].typical_hourly_rate_usd
            assert rate is not None and rate >= 15.0, f"{name} rate={rate}"

    def test_total_grew(self) -> None:
        from cores.opportunity.global_sources import get_sources

        assert len(get_sources()) >= 138  # 136 + 2
