"""Guards del adapter de AI-evaluación (Mercor).

El invariante central es de honestidad, no de cobertura: una oportunidad
**sin rate publicado no puede entrar al ranking**. Emitirla con `payment=0`
y unas horas estimadas fabrica un `$/hora` que nadie puede cobrar, que es
exactamente el fallo que este adapter existe para no repetir.

Los tests son offline: parchean el HTTP y parsean un fixture con la forma
real del payload (`__NEXT_DATA__` de Next.js) medida el 2026-10-01.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from api.adapters.direct_work_ai_eval import (
    TECH_DOMAINS,
    AiEvaluationDweAdapter,
)


def _next_data(listings: list[dict[str, Any]]) -> str:
    """Reproduce la forma real del payload que Mercor sirve al navegador."""
    payload = {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": [{"state": {"data": {"listings": listings}}}],
                }
            }
        }
    }
    body = json.dumps(payload)
    return f'<html><script type="application/json" id="__NEXT_DATA__">{body}</script></html>'


def _listing(**over: Any) -> dict[str, Any]:
    base = {
        "title": "Software Engineer Expert",
        "listingId": "list_ABC123",
        "listingDomain": "Software Engineering",
        "rateMin": 100,
        "rateMax": 150,
        "payRateFrequency": "hourly",
        "eligibleLocation": [],
        "location": "Remote",
        "hoursPerWeek": 40,
    }
    base.update(over)
    return base


class _FakeClient:
    """httpx.AsyncClient stub: returns the fixture HTML for the jobs page."""

    def __init__(self, html: str, status: int = 200) -> None:
        self._html = html
        self._status = status

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def get(self, url: str, **kwargs: Any) -> Any:
        class _Resp:
            status_code = self._status
            text = self._html

        return _Resp()


def _patch_client(monkeypatch: pytest.MonkeyPatch, html: str, status: int = 200) -> None:
    import api.adapters.direct_work_ai_eval as mod

    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda *a, **k: _FakeClient(html, status))


# ══════════════════════════════════════════════════════════════════
# 1. La regla de honestidad: sin rate ⇒ no existe
# ══════════════════════════════════════════════════════════════════


def test_listing_sin_rate_no_se_emite(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un listing sin cifra publicada jamás entra como `$0`."""
    _patch_client(monkeypatch, _next_data([_listing(rateMin=0, rateMax=0)]))
    opps = _run(AiEvaluationDweAdapter())
    assert opps == [], "una oportunidad sin rate publicado no es una oportunidad"


def test_rate_no_normalizable_no_se_emite(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pago por proyecto sin esfuerzo conocido ⇒ $/h UNKNOWN, no inventado."""
    _patch_client(monkeypatch, _next_data([_listing(payRateFrequency="fixed")]))
    assert _run(AiEvaluationDweAdapter()) == []


def test_sin_rate_no_hay_horas_inventadas(monkeypatch: pytest.MonkeyPatch) -> None:
    """El denominador de un $/h no se inventa: sin rate, no hay nada.

    Guard reforzado: además del resultado, se fija que `_to_hourly` **no**
    convierta una tasa ausente en un número. Reintroducir el fallo
    (devolver 1.0 en vez de 0.0) debe hacer caer este test.
    """
    _patch_client(monkeypatch, _next_data([_listing(rateMin=0)]))
    assert _run(AiEvaluationDweAdapter()) == []

    adapter = AiEvaluationDweAdapter()
    assert adapter._to_hourly(0.0, "hourly") == 0.0
    assert adapter._to_hourly(100.0, "") == 0.0, "frecuencia desconocida ⇒ UNKNOWN"
    assert adapter._to_hourly(100.0, "fixed") == 0.0, "proyecto sin esfuerzo ⇒ UNKNOWN"


def test_rate_ausente_no_llega_como_cero_que_hace_parecer_barato(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un `$0` con horas estimadas es un $/h-ranking error: se descarta entero.

    Este es el fallo exacto que motivó el adapter: el discovery de GitHub
    emitía 94 oportunidades con `reward=0` y 8h estimadas.
    """
    _patch_client(monkeypatch, _next_data([_listing(rateMin=0, rateMax=0, payRateFrequency="hourly")]))
    emitted = _run(AiEvaluationDweAdapter())
    assert emitted == [], f"se emitieron {len(emitted)} oportunidades sin pago"


def test_la_guarda_de_rate_existe_y_descarta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin explícito: quitar la guarda `rate_min` debe romper este test.

    La guarda y la normalización son dos filtros; este test fija el primero
    para que no se elimine como "redundante" y quede un solo punto de fallo.
    """
    import inspect

    src = inspect.getsource(AiEvaluationDweAdapter._convert)
    assert "if rate_min <= 0.0:" in src, "la guarda de rate published se eliminó"
    assert "UNKNOWN is not $0" in src, "se perdió la razón documentada de la guarda"


# ══════════════════════════════════════════════════════════════════
# 2. Zero barrier (el objetivo: sin experiencia ni entrevista)
# ══════════════════════════════════════════════════════════════════


def test_oportunidad_no_exige_experiencia_ni_entrevista(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, _next_data([_listing()]))
    (opp,) = _run(AiEvaluationDweAdapter())
    assert opp.interview_required is False
    assert opp.experience_required.value == "none"
    assert opp.portfolio_required is False
    assert opp.category.value == "ai_evaluation"


def test_tasa_publicada_llega_como_hourly_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, _next_data([_listing(rateMin=125, rateMax=175)]))
    (opp,) = _run(AiEvaluationDweAdapter())
    assert opp.hourly_rate_usd == 125.0
    assert opp.rate_source == "mercor", "una cifra scrapeada es observada, no asumida"


# ══════════════════════════════════════════════════════════════════
# 3. Filtros: dominio técnico y geografía
# ══════════════════════════════════════════════════════════════════


def test_dominio_no_tecnico_se_descarta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Medicina/legal no es comparable con un $/h de software."""
    _patch_client(monkeypatch, _next_data([_listing(listingDomain="Medicine")]))
    assert _run(AiEvaluationDweAdapter()) == []


def test_listing_restringido_a_usa_se_descarta(monkeypatch: pytest.MonkeyPatch) -> None:
    """No podemos aceptar un puesto elegible solo en USA."""
    _patch_client(monkeypatch, _next_data([_listing(eligibleLocation=["USA"])]))
    assert _run(AiEvaluationDweAdapter()) == []


def test_listing_sin_restriccion_geografica_se_acepta(monkeypatch: pytest.MonkeyPatch) -> None:
    """`eligibleLocation: []` = Remote sin restricción (medido 2026-10-01)."""
    _patch_client(monkeypatch, _next_data([_listing(eligibleLocation=[])]))
    assert len(_run(AiEvaluationDweAdapter())) == 1


def test_tecnologia_es_el_unico_dominio_aceptado() -> None:
    assert "software engineering" in TECH_DOMAINS
    assert "medicine" not in TECH_DOMAINS and "law" not in TECH_DOMAINS


# ══════════════════════════════════════════════════════════════════
# 4. Robustez: la red puede caer
# ══════════════════════════════════════════════════════════════════


def test_error_de_red_no_rompe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Discovery aísla errores: una caída devuelve vacío, nunca una excepción."""
    import api.adapters.direct_work_ai_eval as mod

    class _Boom:
        def __init__(self, *a: object, **k: object) -> None:
            raise RuntimeError("network down")

    monkeypatch.setattr(mod.httpx, "AsyncClient", _Boom)
    assert _run(AiEvaluationDweAdapter()) == []


def test_http_500_devuelve_vacio(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, "<html>error</html>", status=500)
    assert _run(AiEvaluationDweAdapter()) == []


def test_html_sin_payload_no_inventa_nada(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, "<html><body>sin datos</body></html>")
    assert _run(AiEvaluationDweAdapter()) == []


def test_validate_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, _next_data([]), status=200)
    assert _run_bool(AiEvaluationDweAdapter().validate_connection()) is True


# ══════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════


def _run(adapter: AiEvaluationDweAdapter) -> list[Any]:
    import asyncio

    return asyncio.run(adapter.fetch_opportunities())


def _run_bool(coro: Any) -> bool:
    import asyncio

    return asyncio.run(coro)
