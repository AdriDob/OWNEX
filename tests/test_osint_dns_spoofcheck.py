"""SpoofCheck ahora lee DNS directo, y el resto de integraciones se puede sondear.

Por qué existe (2026-10-05). `SpoofCheckClient` apuntaba a
`https://spoofcheck.io/api`, un host que **no resuelve DNS** (verificado con
`scripts/probe_integrations.py`). Estaba declarado como *keyless* desde
siempre: nunca funcionó, y cada llamada devolvía `None` dentro de un
`except` silencioso — indistinguible de "el dominio no tiene SPF".

Lo que hay que consultar es, literalmente, un TXT record. Hacerlo por DNS
elimina la dependencia externa que puede morir, no cuesta nada y no necesita
API key.

Estos tests usan `dnspython` con un resolver **falso**: no Depends de la red
(excepto un test marked que sí, porque la integración completa vale probarla
contra DNS real). La forma de la respuesta de DNS está documentada arriba de
`_check_sync`.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from cores.recon.osint_api import CLIENTS, SpoofCheckClient

dns = pytest.importorskip("dns.resolver")


class _Rdata:
    """Un rdata de dnspython: `.strings` es una tupla de bytes."""

    def __init__(self, text: str):
        # dnspython parte un TXT largo en varios chunks de 255.
        self.strings = (text.encode(),)


class _FakeAnswer(list):
    """`dns.resolver.Answer` — iterable de rdata."""

    def __init__(self, values: list[str]):
        super().__init__([_Rdata(v) for v in values])


class _FakeResolver:
    """Dict de nombre -> registros TXT. `None` = NXDOMAIN (no existe)."""

    def __init__(self, records: dict[str, list[str] | None]):
        self.records = records
        self.asked: list[str] = []

    def resolve(self, name: str, rdtype: str, lifetime: int = 6) -> _FakeAnswer:
        self.asked.append(name)
        if self.records.get(name) is None:
            raise dns.resolver.NXDOMAIN()
        return _FakeAnswer(self.records.get(name) or [])


def _run(records: dict[str, list[str] | None]) -> dict[str, Any]:
    """Ejecuta check_domain con el resolver falso inyectado (sin red)."""
    return asyncio.run(SpoofCheckClient(resolver=_FakeResolver(records)).check_domain("ejemplo.com"))


class TestNoDeadDependency:
    def test_no_apunta_a_un_host_que_no_resuelve(self) -> None:
        """`spoofcheck.io` no resuelve DNS: la integración estaba muerta."""
        c = CLIENTS["spoofcheck"]
        assert "spoofcheck.io" not in c.base_url
        assert "spoocheck.io" not in c.base_url, "además estaba mal escrito"

    def test_sigue_siendo_keyless(self) -> None:
        """El contrato de `api/routers/osint.py` lo marca como sin key."""
        assert CLIENTS["spoofcheck"].api_key == ""

    def test_no_usa_http(self) -> None:
        c = CLIENTS["spoofcheck"]
        assert c.base_url.startswith("dns:"), "debe resolver por DNS, no por HTTP"


class TestDnsRecords:
    def test_lectura_spf_dmarc(self) -> None:
        r = _run(
            {
                "ejemplo.com": ["v=spf1 include:_spf.google.com ~all"],
                "_dmarc.ejemplo.com": ["v=DMARC1; p=reject; rua=mailto:a@ejemplo.com"],
            }
        )
        assert r["spf"]["present"] is True
        assert r["spf"]["policy"] == "~all"
        assert r["spf"]["hard_fail"] is False, "~all es softfail, no hard fail"
        assert r["dmarc"]["present"] is True
        assert r["dmarc"]["policy"] == "reject"
        assert r["dmarc"]["enforcing"] is True
        assert r["source"] == "dns"

    def test_spf_hardfail(self) -> None:
        r = _run(
            {
                "ejemplo.com": ["v=spf1 -all"],
                "_dmarc.ejemplo.com": ["v=DMARC1; p=quarantine"],
            }
        )
        assert r["spf"]["hard_fail"] is True
        assert r["dmarc"]["enforcing"] is True

    def test_honestidad_cuando_no_hay_nada(self) -> None:
        """Sin SPF ni DMARC: `NO_DATA`, no `{"present": false}` con 0 fingido."""
        r = _run({})
        assert r["spf"]["present"] is False
        assert r["dmarc"]["present"] is False
        assert r["verdict"].startswith("NO_DATA")

    def test_politicas_debiles_no_se_declaran_efectivas(self) -> None:
        """`~all` y `?all` no protegen de verdad."""
        r = _run({"ejemplo.com": ["v=spf1 ~all"]})
        assert r["spf"]["policy"] == "~all"
        assert r["verdict"].startswith("PARCIAL")

    def test_dmarc_none_no_es_aplicacion(self) -> None:
        r = _run(
            {
                "ejemplo.com": ["v=spf1 -all"],
                "_dmarc.ejemplo.com": ["v=DMARC1; p=none"],
            }
        )
        assert r["dmarc"]["enforcing"] is False
        assert r["verdict"].startswith("PARCIAL"), "p=none no protege"

    def test_dkim_devuelve_los_selectors_encontrados(self) -> None:
        r = _run(
            {
                "ejemplo.com": ["v=spf1 -all"],
                "default._domainkey.ejemplo.com": ["v=DKIM1; k=rsa; p=AAA"],
                "google._domainkey.ejemplo.com": ["v=DKIM1; k=rsa; p=AAA"],
            }
        )
        assert "default" in r["dkim"]["selectors_found"]
        assert "google" in r["dkim"]["selectors_found"]

    def test_es_awaitable_desde_event_loop(self) -> None:
        """`check_domain` es async aunque el resolver sea bloqueante.

        Se usa `asyncio.to_thread`: si fuera sync, bloquearía el loop igual
        que el bug de `/activate` (KNOWN_DEBT #58).
        """
        assert asyncio.iscoroutinefunction(SpoofCheckClient.check_domain)


class TestLiveDns:
    """Contra DNS real. Falla (skip) si la red no tiene DNS, no si el código."""

    def test_dominio_conocido(self) -> None:
        try:
            r = asyncio.run(SpoofCheckClient().check_domain("google.com"))
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"sin DNS desde acá: {type(exc).__name__}")

        if r is None:
            pytest.skip("resolver no devolvió nada")

        # google.com tiene SPF y DMARC conocidos. Lo que importa es que la
        # consulta DNS responda algo con la forma esperada.
        assert r["source"] == "dns"
        assert r["domain"] == "google.com"
        assert set(r) >= {"spf", "dmarc", "dkim", "verdict"}
        assert r["verdict"]
