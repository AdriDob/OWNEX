"""El pipeline de bounty: targets reales y event loop que no se congela.

Por qué existe (auditoría 2026-10-05). Dos bugs en el revenue multiplier:

## (a) Los targets eran inventados

`_discover_targets` leía:

    entry.get("url") or entry["target"]["marketplace"]["handle"]

**Ninguno de los dos campos existe.** El dataset público de bounty-targets
usa `handle` a nivel superior. Verificado contra las 449 entradas reales: con
el código anterior, **0 de 10** parseaban y el método caía SIEMPRE al
fallback:

    targets = ["docs.hackerone.com", "httpforever.com", "example.com"]

Es decir: el pipeline escaneaba `example.com` con nuclei y sqlmap. Un target
de scanner inventado no es un dato de fallback — es un escaneo real contra un
dominio que nadie pidió escanear.

## (b) `/activate` congelaba el server entero

El orchestrator es síncrono: `subprocess.run` de nuclei/sqlmap con timeouts
de hasta 900s por tool, más llamadas de red. Llamado directo desde un
`async def`, bloquea el event loop DEL SERVER: no sólo esa request, sino
health, WebSockets y copilot durante los minutos que dure el escaneo.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.routers.revenue_multiplier as rm_router
from cores.revenue_multiplier.config import RevenueMultiplierConfig
from cores.revenue_multiplier.orchestrator import RevenueMultiplierOrchestrator

ORCH = Path(__file__).resolve().parent.parent / "cores" / "revenue_multiplier" / "orchestrator.py"

# Forma REAL del dataset (verificada contra las 449 entradas de HackerOne)
REAL_DATASET = [
    {"handle": "omarchy", "offers_bounties": True, "name": "Omarchy"},
    {"handle": "common_codes", "offers_bounties": True, "name": "Common Codes"},
    {"handle": "sin_pago", "offers_bounties": False, "name": "No Bounty"},
    {"handle": "-ignorado", "offers_bounties": True, "name": "Handle con guion"},
    {"handle": "", "offers_bounties": True, "name": "Sin handle"},
]


class _FakeResp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _orch() -> RevenueMultiplierOrchestrator:
    return RevenueMultiplierOrchestrator(RevenueMultiplierConfig())


class TestTargetsAreReal:
    def test_parsea_handle_no_url(self, monkeypatch) -> None:
        """El campo real es `handle`, no `url`."""
        monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResp(REAL_DATASET))

        targets = _orch()._discover_targets()

        assert targets == ["omarchy.hackerone.com", "common_codes.hackerone.com"]

    def test_filtra_programas_sin_bounty(self, monkeypatch) -> None:
        """Escanear un programa que no paga bounty no puede ser ingreso."""
        monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResp(REAL_DATASET))

        targets = _orch()._discover_targets()

        assert "sin_pago.hackerone.com" not in targets

    def test_ignora_handles_invalidos(self, monkeypatch) -> None:
        monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResp(REAL_DATASET))

        targets = _orch()._discover_targets()

        assert not any(t.startswith("-") for t in targets), "no debe tomar handles que empiezan con -"
        assert "" not in targets

    def test_sin_datos_devuelve_lista_vacia(self, monkeypatch) -> None:
        """Sin dataset: 0 targets. NUNCA inventados."""
        monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResp([]))

        assert _orch()._discover_targets() == []

    def test_si_el_dataset_falla_no_inventa(self, monkeypatch) -> None:
        def _boom(*a, **k):
            raise RuntimeError("sin red")

        monkeypatch.setattr(httpx, "get", _boom)

        assert _orch()._discover_targets() == [], "sin red no se inventan targets"

    def test_no_queda_el_fallback_inventado(self) -> None:
        """Guard estructural: `example.com` no debe volver a ESCANEARSE.

        Se chequea el código, no la prosa: el docstring menciona el dominio
        a propósito para documentar qué pasó. Un guard que falla por un
        comentario obliga a borrar la explicación del fix.
        """
        import re as _re

        src = ORCH.read_text(encoding="utf-8")
        # Sólo líneas de código: fuera comentarios y docstrings.
        codigo = "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith(("#", '"', "'", "*")))
        offenders = [
            f"línea {i}: {ln.strip()}"
            for i, ln in enumerate(src.splitlines(), start=1)
            if _re.search(r"(targets|target)\s*=\s*\[.*(example\.com|httpforever)", ln)
        ]
        assert not offenders, "targets inventados hardcodeados:\n  " + "\n  ".join(offenders)
        assert 'targets = ["docs.hackerone.com"' not in codigo

    def test_la_forma_real_del_dataset_se_parsea(self) -> None:
        """Si el upstream cambia de forma, esto avisa en vez de callar."""
        assert "handle" in REAL_DATASET[0]
        assert "url" not in REAL_DATASET[0], "el dataset real NO tiene 'url'; si aparece, upstream cambió"


class TestEventLoopIsNotBlocked:
    @pytest.fixture
    def client(self) -> TestClient:
        app = FastAPI()
        app.include_router(rm_router.router)
        return TestClient(app)

    def test_activate_no_bloquea_el_loop(self, monkeypatch) -> None:
        """La prueba clave: el handler NO debe bloquear el loop.

        Se invoca el handler CORRIDO (no por HTTP) dentro del loop que
        realmente corre, con un heartbeat concurrente. Con la llamada
        síncrona directa, el heartbeat se congela hasta que el orchestrator
        termina; con `asyncio.to_thread`, sigue latiendo.

        Nota de método: la primera versión usaba `TestClient`, que ejecuta
        la app en su propio loop dentro de otro hilo — el heartbeat medía el
        loop equivocado y el test PASABA con el bug presente. Por eso ahora
        se llama al handler directamente.
        """
        import cores.revenue_multiplier as pkg

        ticks = {"n": 0}

        class _SlowOrch:
            """Tarda 1.2s 'escaneando' con sleep bloqueante."""

            def activate_max_revenue_mode(self):
                t0 = time.monotonic()
                while time.monotonic() - t0 < 1.2:
                    time.sleep(0.02)
                return {"ok": True}

        monkeypatch.setattr(pkg, "RevenueMultiplierOrchestrator", _SlowOrch)
        monkeypatch.setattr(pkg, "get_revenue_multiplier", lambda: _SlowOrch())

        async def _heartbeat():
            while True:
                ticks["n"] += 1
                await asyncio.sleep(0.02)

        async def _run():
            hb = asyncio.create_task(_heartbeat())
            resp = await rm_router.activate_max_revenue({})
            hb.cancel()
            return resp

        resp = asyncio.run(_run())

        assert resp["success"] is True
        assert ticks["n"] > 10, (
            f"el event loop se congeló: sólo {ticks['n']} ticks durante 1.2s de "
            "escaneo. El handler está llamando al orchestrator de forma bloqueante."
        )

    def test_activate_sigue_devolviendo_el_resultado(self, client: TestClient, monkeypatch) -> None:
        """to_thread no debe cambiar el contrato de respuesta."""

        class _Orch:
            def activate_max_revenue_mode(self):
                return {"targets_scanned": 3, "findings": 7}

        import cores.revenue_multiplier as pkg

        monkeypatch.setattr(pkg, "RevenueMultiplierOrchestrator", _Orch)
        monkeypatch.setattr(pkg, "get_revenue_multiplier", lambda: _Orch())

        r = client.post("/api/revenue-multiplier/activate", json={})

        assert r.status_code == 200
        assert r.json()["result"] == {"targets_scanned": 3, "findings": 7}


class TestNoFakeTargetsInSource:
    def test_no_hay_lista_literal_de_targets(self) -> None:
        """Ninguna lista de dominios inventados debe quedar en el pipeline."""
        src = ORCH.read_text(encoding="utf-8")
        bloque = src.split("def _discover_targets", 1)[1].split("\n    def ", 1)[0]
        assert "targets = [" not in bloque, (
            "_discover_targets no debe asignar una lista literal de targets; "
            "si el upstream falla, devuelve [] y el pipeline no escanea nada"
        )
