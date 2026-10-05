"""Guards del adapter de directorios de bug bounty.

El invariante es de honestidad, no de cobertura: un programa **sin rango
publicado no entra**. Emitirlo con `$0` fue exactamente lo que hizo el
discovery de GitHub bounty (94 oportunidades, 0 con pago parseado) y
convirtió ruido en pipeline.

Y una regla que este archivo fija para que no se repita: **una cifra que
no se puede atribuir a un programa no se publica**. YesWeHack devuelve 200
con 366 KB de rangos, pero el markup no aísla un programa por link, así que
su número puede pertenecer a otro: no se registra como plataforma.
"""

from __future__ import annotations

from typing import Any

import pytest

from api.adapters.direct_work_bug_bounty_directory import (
    _MAX_PROGRAM_REWARD_USD,
    PLATFORMS,
    BugBountyDirectoryDweAdapter,
)


def _card(href: str, name: str, low: int, high: int, pad: int = 0) -> str:
    """One server-rendered program card, as the directory renders it.

    `pad` inserts filler so the figure sits far from its own link — the
    real page measured 1 017–24 624 chars of distance, which is why a
    fixed window silently borrowed another program's number.
    """
    filler = "<span>" + ("irrelevant text " * (pad // 17)) + "</span>" if pad else ""
    return (
        f'<a href="{href}">View program</a>'
        f"{filler}"
        f"${low:,} – ${high:,}"
        f"<h4>{name}</h4>"
        f'<span class="text-muted">Vulnerability Disclosure</span>'
    )


def _page(cards: list[str]) -> str:
    return "<html><body>" + "".join(cards) + "</body></html>"


class _Resp:
    def __init__(self, status: int, text: str) -> None:
        self.status_code = status
        self.text = text


class _Client:
    def __init__(self, html: str, status: int = 200) -> None:
        self._html = html
        self._status = status

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def get(self, url: str, **kw: object) -> _Resp:
        return _Resp(self._status, self._html)

    async def aclose(self) -> None:
        return None


def _patch(monkeypatch: pytest.MonkeyPatch, html: str, status: int = 200) -> None:
    import api.adapters.direct_work_bug_bounty_directory as mod

    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda *a, **k: _Client(html, status))


def _run() -> list[Any]:
    import asyncio

    return asyncio.run(BugBountyDirectoryDweAdapter(PLATFORMS[0]).fetch_opportunities())


# ══════════════════════════════════════════════════════════════════
# 1. Sin rango publicado ⇒ no existe
# ══════════════════════════════════════════════════════════════════


def test_programa_sin_rango_no_se_emite(monkeypatch: pytest.MonkeyPatch) -> None:
    href = "https://app.intigriti.com/programs/acme/vdp"
    _patch(monkeypatch, _page([f'<a href="{href}">View program</a><h4>Acme</h4>']))
    assert _run() == [], "sin rango publicado no es una oportunidad"


def test_rango_sin_marca_de_moneda_no_cuenta(monkeypatch: pytest.MonkeyPatch) -> None:
    """'2500 tests' es un número, no un payout."""
    href = "https://app.intigriti.com/programs/acme/vdp"
    _patch(monkeypatch, _page([f'<a href="{href}">View program</a>2500 tests<h4>Acme</h4>']))
    assert _run() == []


# ══════════════════════════════════════════════════════════════════
# 2. El techo del rango, no el piso
# ══════════════════════════════════════════════════════════════════


def test_reporta_el_techo_del_rango(monkeypatch: pytest.MonkeyPatch) -> None:
    """`$75 – $15,000`: el primer número es el piso.

    Reportar $75 y llamarlo "hasta $X" subestima el payout real; el
    valor que se publica es el máximo del rango.
    """
    href = "https://app.intigriti.com/programs/adobe/adobepublic"
    _patch(monkeypatch, _page([_card(href, "Adobe", 75, 15_000)]))
    (opp,) = _run()
    assert opp.payment == 15_000.0
    assert "$15,000" in opp.description


def test_sufijos_k_y_m(monkeypatch: pytest.MonkeyPatch) -> None:
    href = "https://app.intigriti.com/programs/a/b"
    _patch(monkeypatch, _page([f'<a href="{href}">View program</a>$2k – $3k<h4>A</h4>']))
    assert _run()[0].payment == 3_000.0


def test_cifra_absurda_es_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un número pegado que excede el techo medido no es un payout."""
    href = "https://app.intigriti.com/programs/a/b"
    huge = "9" * 30
    _patch(monkeypatch, _page([f'<a href="{href}">View program</a>${huge}<h4>A</h4>']))
    assert _run() == []


def test_el_techo_global_es_acotado() -> None:
    assert 0 < _MAX_PROGRAM_REWARD_USD <= 1_000_000.0


# ══════════════════════════════════════════════════════════════════
# 3. Atribución: el importe es del programa de ese link
# ══════════════════════════════════════════════════════════════════


def test_cada_programa_toma_su_propio_rango(monkeypatch: pytest.MonkeyPatch) -> None:
    """El caso que motivó dividir por link en vez de usar una ventana.

    Medido: la distancia del link a su cifra iba de 1.017 a 24.624
    caracteres, así que una ventana fija prestaba el número de otro
    programa.
    """
    cards = [
        _card("https://app.intigriti.com/programs/adobe/adobepublic", "Adobe", 75, 15_000, pad=3_000),
        _card("https://app.intigriti.com/programs/nvidia/nvidiapublic", "Nvidia", 150, 15_000, pad=12_000),
        _card("https://app.intigriti.com/programs/coveo/coveopublic", "Coveo", 100, 5_500, pad=6_000),
    ]
    _patch(monkeypatch, _page(cards))
    got = {o.title.split("] ")[-1]: o.payment for o in _run()}
    assert got == {"Adobe": 15_000.0, "Nvidia": 15_000.0, "Coveo": 5_500.0}


def test_una_ventana_corta_robaria_la_cifra_del_vecino(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard directo del fallo medido: con ventana, Adobe tomaba $100 de Coveo.

    Las cifras están a 3 000/12 000/6 000 caracteres de su propio link
    (rango real observado: 1 017–24 624). Cualquier ventana fija o bien
    pierde el payout o bien lee el del programa vecino.
    """
    cards = [
        _card("https://app.intigriti.com/programs/adobe/adobepublic", "Adobe", 75, 15_000, pad=3_000),
        _card("https://app.intigriti.com/programs/coveo/coveopublic", "Coveo", 100, 5_500, pad=1_500),
    ]
    _patch(monkeypatch, _page(cards))
    adobe = next(o for o in _run() if "Adobe" in o.title)
    coveo = next(o for o in _run() if "Coveo" in o.title)
    assert adobe.payment == 15_000.0
    assert coveo.payment == 5_500.0
    assert adobe.payment != coveo.payment


def test_titulo_no_es_el_label_generico(monkeypatch: pytest.MonkeyPatch) -> None:
    """ "Programs" como nombre de 15 programas no sirve para decidir."""
    href = "https://app.intigriti.com/programs/yeswehack/programs"
    _patch(monkeypatch, _page([f'<a href="{href}">$500 – $900<h4>Programs</h4>']))
    opp = _run()[0]
    assert not opp.title.endswith("Programs"), "el nombre genérico debe caer al slug del dueño"
    assert "Yeswehack" in opp.title


def test_dedup_por_url(monkeypatch: pytest.MonkeyPatch) -> None:
    href = "https://app.intigriti.com/programs/a/b"
    _patch(monkeypatch, _page([_card(href, "A", 10, 20), _card(href, "A", 10, 20)]))
    assert len(_run()) == 1


# ══════════════════════════════════════════════════════════════════
# 4. Zero barrier + red caída
# ══════════════════════════════════════════════════════════════════


def test_oportunidad_es_zero_barrier(monkeypatch: pytest.MonkeyPatch) -> None:
    href = "https://app.intigriti.com/programs/adobe/adobepublic"
    _patch(monkeypatch, _page([_card(href, "Adobe", 75, 15_000)]))
    (opp,) = _run()
    assert opp.experience_required.value == "none"
    assert opp.interview_required is False
    assert opp.portfolio_required is False
    # effort UNKNOWN: inventar las horas fabrica el $/h
    assert opp.estimated_time_hours == 0.0


def test_http_500_devuelve_vacio(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, "<html>error</html>", status=500)
    assert _run() == []


def test_error_de_red_no_rompe(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.adapters.direct_work_bug_bounty_directory as mod

    class _Boom:
        def __init__(self, *a: object, **k: object) -> None:
            raise RuntimeError("network down")

    monkeypatch.setattr(mod.httpx, "AsyncClient", _Boom)
    assert _run() == []


def test_html_vacio_no_inventa(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, "")
    assert _run() == []


# ══════════════════════════════════════════════════════════════════
# 5. Sólo plataformas verificables
# ══════════════════════════════════════════════════════════════════


def test_solo_plataformas_con_rango_atribuible() -> None:
    """Bugcrowd (0 parseables) y YesWeHack (no atribuible) no se publican.

    Registrarlas devolvería 0 oportunidades — o peor, cifras que
    pertenecen a otro programa. Documentadas en `PLATFORMS`.
    """
    names = {p.name for p in PLATFORMS}
    assert names == {"intigriti"}
