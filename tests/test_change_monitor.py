"""Tests P2+P3 — change monitor (baselines/deltas/alertas) + plantillas custom.

Todo offline: el fetcher se inyecta, los paths usan tmp, el runner nuclei
se mockea. Ningún test toca red ni credenciales.
"""

from __future__ import annotations

import asyncio


def _cm(tmp_path, monkeypatch):
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
    from cores.recon.change_monitor import ChangeMonitor

    return ChangeMonitor()


class TestExtractRoutes:
    def test_fetch_axios_y_api(self):
        from cores.recon.change_monitor import extract_js_routes

        js = 'fetch("/api/users?page=1"); axios.post("/v2/orders", {}); var u = "/graphql";'
        routes = extract_js_routes(js)
        assert "/api/users?page=1" in routes
        assert "/v2/orders" in routes
        assert "/graphql" in routes

    def test_vacio_y_basura(self):
        from cores.recon.change_monitor import extract_js_routes

        assert extract_js_routes("") == []
        assert extract_js_routes(None) == []  # type: ignore[arg-type]
        assert isinstance(extract_js_routes("var x = 1;"), list)


class TestInteresting:
    def test_graphql_admin_secreto_alertan(self):
        from cores.recon.change_monitor import interesting_signals

        assert interesting_signals(["/graphql", "/x"]) != []
        assert interesting_signals(["/admin/panel"], "nada") != []
        assert interesting_signals([], 'api_key = "ABCD1234"') != []

    def test_ruido_no_alerta(self):
        from cores.recon.change_monitor import interesting_signals

        assert interesting_signals(["/about", "/contact"]) == []
        assert interesting_signals([], "hola mundo") == []


class TestBaselines:
    def test_primera_vez_es_baseline_sin_alerta(self, tmp_path, monkeypatch):
        monitor = _cm(tmp_path, monkeypatch)
        d = monitor.diff("t::https://x.test/", "hola")
        assert d["first_seen"] is True
        assert d["changed"] is False

    def test_cambio_detecta_nuevas_rutas_y_persiste(self, tmp_path, monkeypatch):
        from cores.recon.change_monitor import ChangeMonitor

        m1 = _cm(tmp_path, monkeypatch)
        m1.diff("t::https://x.test/", "var a = 1;")
        d = m1.diff("t::https://x.test/", 'fetch("/api/admin/users");')
        assert d["changed"] is True
        assert "/api/admin/users" in d["new_routes"]
        m2 = ChangeMonitor()  # recarga del mismo store
        d2 = m2.diff("t::https://x.test/", 'fetch("/api/admin/users");')
        assert d2["changed"] is False

    def test_sin_cambio_no_hay_delta(self, tmp_path, monkeypatch):
        monitor = _cm(tmp_path, monkeypatch)
        monitor.diff("k", "mismo")
        assert monitor.diff("k", "mismo")["changed"] is False


class TestCycle:
    def test_ciclo_con_fetcher_falso_solo_alerta_interesante(self, tmp_path, monkeypatch):
        from cores.recon.change_monitor import run_change_cycle

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        pages: dict[str, str | None] = {
            "https://a.test/": "home",
            "https://b.test/": 'fetch("/api/public/info");',
        }
        out = run_change_cycle({"a": ["https://a.test/"], "b": ["https://b.test/"]}, fetcher=pages.get)
        assert out["checked"] == 2
        assert out["alerts"] == 0  # primera vuelta = baselines
        pages["b.test/"] = None
        pages["https://b.test/"] = 'fetch("/api/public/info"); fetch("/graphql");'
        out2 = run_change_cycle({"b": ["https://b.test/"]}, fetcher=pages.get)
        assert out2["changed"] == 1
        assert out2["alerts"] == 1

    def test_fetcher_que_falla_es_skip(self, tmp_path, monkeypatch):
        from cores.recon.change_monitor import run_change_cycle

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))

        def boom(url):
            raise ConnectionError("down")

        out = run_change_cycle({"a": ["https://a.test/"]}, fetcher=boom)
        assert out["skipped"] == 1
        assert out["alerts"] == 0

    def test_sin_fetcher_no_raisea(self, tmp_path, monkeypatch):
        from cores.recon.change_monitor import run_change_cycle

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        out = run_change_cycle({"a": ["https://a.test/"]})
        assert out["checked"] == 0

    def test_alertas_recientes(self, tmp_path, monkeypatch):
        from cores.recon.change_monitor import ChangeMonitor

        monitor = _cm(tmp_path, monkeypatch)
        monitor.record_alert({"key": "k", "url": "u", "signals": ["s"]})
        assert len(ChangeMonitor().recent_alerts()) == 1


class TestCustomTemplates:
    def test_genera_solo_prioritarios_y_no_pisa(self, tmp_path):
        from cores.intel.cve_intel import CVEResult, suggest_custom_templates

        def _cve(cid, score):
            return CVEResult(
                id=cid,
                cvss=9.0,
                epss=0.9,
                priority_score=score,
                description="d" * 10,
                kev=True,
                tech="nginx",
                priority_label="Critical",
                fix="upgrade",
                url="https://x",
            )

        out = suggest_custom_templates([_cve("CVE-2026-0001", 9.0), _cve("CVE-2026-0002", 3.0)], out_dir=str(tmp_path))
        assert out["success"] is True
        assert out["created"] == ["custom-cve-2026-0001.yaml"]
        body = (tmp_path / "custom-cve-2026-0001.yaml").read_text()
        assert "draft: true" in body
        # Segunda corrida no pisa trabajo humano
        (tmp_path / "custom-cve-2026-0001.yaml").write_text("EDITADO")
        out2 = suggest_custom_templates([_cve("CVE-2026-0001", 9.0)], out_dir=str(tmp_path))
        assert out2["created"] == []
        assert (tmp_path / "custom-cve-2026-0001.yaml").read_text() == "EDITADO"

    def test_nuclei_acepta_template_dirs(self, tmp_path, monkeypatch):
        import cores.recon.nuclei_runner as nr

        captured: dict = {}

        class FakeProc:
            async def communicate(self):
                return b"", b""

        async def fake_exec(*cmd, **kw):
            captured["cmd"] = list(cmd)
            return FakeProc()

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
        runner = nr.NucleiRunner(tmp_path)
        custom = tmp_path / "custom"
        custom.mkdir()
        target = tmp_path / "t.txt"
        target.write_text("https://x.test\n")
        asyncio.run(runner.run_nuclei(target, template_dirs=[str(custom), "/no/existe"]))
        assert "-t" in captured["cmd"]
        assert str(custom) in captured["cmd"]
        assert "/no/existe" not in captured["cmd"]


class TestHandlerAndJob:
    def test_handler_no_raisea_db_vacia(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        from cores.cycles.tasks import run_change_watch

        out = run_change_watch()
        assert out["status"] in ("ok", "error")
        assert "targets" in out or "message" in out

    def test_job_registrado_y_handler_resuelve(self):
        import importlib

        from cores.scheduler.jobs import get_security_jobs

        jobs = {j.job_id: j for j in get_security_jobs()}
        assert "security_change_watch" in jobs
        handler = jobs["security_change_watch"].handler
        assert isinstance(handler, str)
        mod, attr = handler.split(":")
        assert callable(getattr(importlib.import_module(mod), attr))

    def test_endpoint_alertas_200(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routers.recon import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        r = client.get("/api/recon/change-alerts")
        assert r.status_code == 200
        assert r.json()["success"] is True


class TestAIScopeWatch:
    def test_ai_scope_targets_tres_programas(self):
        from cores.recon.change_monitor import AI_SCOPE_URLS, ai_scope_targets

        targets = ai_scope_targets()
        assert set(targets) == {"openai_safety", "anthropic_safety", "microsoft_ai"}
        assert all(url.startswith("https://") for urls in targets.values() for url in urls)
        assert set(targets) == set(AI_SCOPE_URLS)

    def test_ciclo_detecta_nueva_ruta_ai(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        from cores.recon.change_monitor import ai_scope_targets, run_change_cycle

        v1 = '<html><body><a href="/api/v1/chat">chat</a></body></html>'
        v2 = '<html><body><a href="/api/v1/chat">chat</a><a href="/api/v1/agents">agents</a></body></html>'
        calls = {"n": 0}

        def fake_fetcher(url: str) -> str:
            calls["n"] += 1
            return v1 if calls["n"] <= 3 else v2

        first = run_change_cycle(ai_scope_targets(), fetcher=fake_fetcher)
        assert first["alerts"] == 0
        second = run_change_cycle(ai_scope_targets(), fetcher=lambda url: v2 + '<a href="/admin/console">c</a>')
        assert second["alerts"] >= 1

    def test_handler_ai_no_raisea(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        from cores.cycles.tasks import run_ai_scope_watch

        out = run_ai_scope_watch()
        assert out["status"] in ("ok", "error")
        assert "targets" in out or "message" in out

    def test_job_ai_registrado_y_handler_resuelve(self):
        import importlib

        from cores.scheduler.jobs import get_security_jobs

        jobs = {j.job_id: j for j in get_security_jobs()}
        assert "security_ai_scope_watch" in jobs
        handler = jobs["security_ai_scope_watch"].handler
        assert isinstance(handler, str)
        mod, attr = handler.split(":")
        assert callable(getattr(importlib.import_module(mod), attr))


class TestFreshDomains:
    def test_fresh_domains_cuenta_alertas_recientes(self, tmp_path, monkeypatch):
        from cores.recon.change_monitor import ChangeMonitor, fresh_domains_with_alerts

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        monitor = ChangeMonitor()
        monitor.record_alert({"key": "a", "url": "https://fresh.test/app.js", "signals": ["s"]})
        monitor.record_alert({"key": "b", "url": "not-a-url", "signals": ["s"]})
        fresh = fresh_domains_with_alerts()
        assert fresh == {"fresh.test": 1}

    def test_fresh_domains_vacio_sin_alertas(self, tmp_path, monkeypatch):
        from cores.recon.change_monitor import fresh_domains_with_alerts

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        assert fresh_domains_with_alerts() == {}
