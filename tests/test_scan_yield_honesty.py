"""Scan-yield honesty (2026-09-18): imposible quemar scans en basura.

Fugas verificadas contra DB real:
- 402/719 targets con `_` en el dominio (slug+".com"): DNS imposible, el scan
  jamás puede producir findings.
- El parser convertía banners ASCII en "endpoints" (host=example.com, score=0).

Contrato nuevo (fail-closed, puro donde se puede):
- `is_valid_hostname` / `scannable_domain` / `has_real_host` en
  `cores/recon/hostname.py`.
- Parser: sin host real no se persiste.
- Scheduler: saltea dominios inválidos sin mutar la DB.
- `create_target` + `POST /targets` + `launch_scan`: 422/plot honesto.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from cores.recon.hostname import has_real_host, is_valid_hostname, scannable_domain
from cores.recon.parser import EndpointParser


class TestValidHostname:
    @pytest.mark.parametrize(
        "host",
        ["example.com", "sub.domain.com.ar", "a-b.co", "EXAMPLE.COM ", "example.com.", "target.com:443"],
    )
    def test_validos_pasan(self, host: str) -> None:
        value = host.split(":")[0] if ":" in host and host.count(":") == 1 and "/" not in host else host
        assert is_valid_hostname(value) is True

    @pytest.mark.parametrize(
        "host",
        [
            "agoda_public.com",  # el bug real: slug + ".com"
            "verily_life_sciences.com",
            "",
            "   ",
            "localhost",
            "nota tld",
            "no-tld",
            "-bad.com",
            "bad-.com",
            "a..com",
            "123.456",
            None,
            123,
        ],
    )
    def test_invalidos_fallan(self, host: object) -> None:
        assert is_valid_hostname(host) is False


class TestScannableDomain:
    def test_domain_gana_y_puerto_se_corta(self) -> None:
        assert scannable_domain("x", "target.com:443") == "target.com"

    def test_fallback_a_name(self) -> None:
        assert scannable_domain("target.com", "") == "target.com"
        assert scannable_domain("target.com", None) == "target.com"

    def test_none_si_todo_invalido(self) -> None:
        assert scannable_domain("hackerone_x", "x_y.com") is None
        assert scannable_domain("", "") is None


class TestRealHost:
    def test_placeholder_no_es_evidencia(self) -> None:
        assert has_real_host("") is False
        assert has_real_host("example.com") is False
        assert has_real_host("EXAMPLE.COM") is False

    def test_host_real_pasa(self) -> None:
        assert has_real_host("target.com") is True


class TestParserQualityGate:
    def test_banners_ascii_no_son_endpoints(self) -> None:
        parser = EndpointParser()
        metas = parser.parse_lines(
            ["__        __", "/ /_____ _/ /____ ____  ___ _", "/_/\\_\\\\_,_/\\__/\\_,_/_//_/\\_,_/"]
        )
        assert metas == []

    def test_urls_reales_sobreviven(self) -> None:
        parser = EndpointParser()
        metas = parser.parse_lines(
            ["https://target.com/api/users/123", "https://target.com/graphql", "not a url at all"]
        )
        hosts = {m.host for m in metas}
        assert "target.com" in hosts
        assert "example.com" not in hosts

    def test_linea_error_json_con_dominio_basura_se_cae(self) -> None:
        parser = EndpointParser()
        line = '{"request": {"method": "GET", "endpoint": "https://verily_life_sciences.com"}, "error": "no address found"}'
        assert parser.parse_lines([line]) == []

    def test_httpx_json_con_url_real_se_conserva(self) -> None:
        parser = EndpointParser()
        metas = parser.parse_lines(['{"url": "https://target.com/api/login", "status": 200}'])
        assert len(metas) == 1 and metas[0].host == "target.com"


class TestCreateTargetGate:
    def test_dominio_invalido_no_crea(self) -> None:
        from api.services.data_service import create_target

        res = create_target("slug-basura-unico-xyz", "agoda_public.com")
        assert res.get("invalid") is True
        assert "reason" in res
        assert "id" not in res

    def test_dominio_vacio_sigue_permitido(self) -> None:
        import uuid

        from api.services.data_service import create_target

        name = f"nodomain-{uuid.uuid4().hex[:8]}"
        res = create_target(name, None)
        assert res.get("invalid") is not True
        assert res["name"] == name


class TestLaunchScanGate:
    def test_scan_a_dominio_invalido_es_422_sin_tools(self) -> None:
        import asyncio

        from cores.orchestrator.scan_service import launch_scan
        from database import db

        session = db.SessionLocal()
        try:
            with pytest.raises(HTTPException) as exc:
                asyncio.run(launch_scan("hackerone_x", "x_y.com", "FAST", session))
            assert exc.value.status_code == 422
        finally:
            session.close()


class TestHypothesisResume:
    def test_endpoint_sin_pipeline_id_igual_genera_hypothesis(self) -> None:
        import asyncio

        from api.scheduler import ScanScheduler
        from database import db, models

        db.init_db()
        session = db.SessionLocal()
        target = models.Target(name="resume-target", domain="resume-target.example.com")
        session.add(target)
        session.commit()
        session.refresh(target)
        ep = models.Endpoint(target_id=target.id, path="/api/users/1", method="GET")
        session.add(ep)
        session.commit()
        ep_id, target_id = ep.id, target.id
        session.close()

        sched = ScanScheduler(interval_minutes=30)
        assert target_id not in sched._target_pipelines
        asyncio.run(sched._stage_hypothesis())

        session = db.SessionLocal()
        try:
            got = session.query(models.Endpoint).get(ep_id)
            assert got is not None and got.hypothesis_id is not None
        finally:
            session.close()
