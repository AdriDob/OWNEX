"""Contratos de los adapters Opire/Opyre legacy contra la API real.

Regresión del bug: ``cores/opportunity/adapters/opire.py`` apuntaba a
``api.opire.com`` / ``api.opyre.com`` — dominios que NO resuelven DNS — y
devolvía ``[]`` en silencio. Resultado: el Work Bank quedaba vacío sin error
visible y el ciclo forge nunca veía oportunidades reales.

Los tres adapters deben:
  1. pegarle a ``https://api.opire.dev/rewards`` (endpoint público verificado)
  2. convertir ``pendingPrice.value`` de USD_CENT a dólares
  3. exponer cuántos claimers tiene el reward (señal de competencia real)
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


PAYLOAD = [
    {
        "id": "01R1",
        "title": "Fix crash on startup",
        "url": "https://github.com/o/r/issues/1",
        "programmingLanguages": ["Python", "Rust"],
        "pendingPrice": {"value": 10000, "unit": "USD_CENT"},
        "claimerUsers": [],
        "tryingUsers": [],
        "project": {"name": "myrepo"},
        "estimatedHours": 2,
    },
    {
        "id": "01R2",
        "title": "Long refactor",
        "url": "https://github.com/o/r/issues/2",
        "pendingPrice": {"value": 4200, "unit": "USD_CENT"},
        "claimerUsers": ["u1", "u2"],
        "tryingUsers": [],
        "project": {"name": "myrepo"},
        "estimatedHours": 8,
    },
    {
        "id": "01R3",
        "title": "No price yet",
        "url": "https://github.com/o/r/issues/3",
        "pendingPrice": None,
        "claimerUsers": [],
        "tryingUsers": [],
        "project": {"name": "myrepo"},
    },
]


def _fake_httpx(monkeypatch: pytest.MonkeyPatch, seen: list[str]) -> None:
    class FakeResp:
        status_code = 200

        def json(self) -> list[dict[str, Any]]:
            return PAYLOAD

    class FakeClient:
        def __init__(self, *a: Any, **kw: Any) -> None:
            pass

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *a: Any) -> None:
            pass

        async def get(self, url: str, headers: dict | None = None, timeout: int = 15) -> FakeResp:
            seen.append(url)
            return FakeResp()

    monkeypatch.setattr("httpx.AsyncClient", FakeClient)


def test_opire_hits_verified_endpoint_and_converts_cents(monkeypatch: pytest.MonkeyPatch) -> None:
    from cores.opportunity.adapters.opire import OpireAdapter

    seen: list[str] = []
    _fake_httpx(monkeypatch, seen)

    opps = _run(OpireAdapter({}).fetch_opportunities())

    assert seen == ["https://api.opire.dev/rewards"]
    assert len(opps) == 3
    assert opps[0].reward == 100.0  # 10000 centavos → $100
    assert opps[1].reward == 42.0
    assert opps[2].reward == 0.0  # pendingPrice None no inventa monto


def test_uncontested_signal_is_exposed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin claimers es la señal de mayor ROI; debe viajar en metadata."""
    from cores.opportunity.adapters.opire import OpireAdapter

    _fake_httpx(monkeypatch, [])

    opps = _run(OpireAdapter({}).fetch_opportunities())

    assert opps[0].metadata["claimers"] == 0
    assert opps[0].metadata["uncontested"] is True
    assert opps[1].metadata["claimers"] == 2
    assert opps[1].metadata["uncontested"] is False


def test_opyre_alias_uses_real_feed(monkeypatch: pytest.MonkeyPatch) -> None:
    """``api.opyre.com`` no existe: el alias debe usar el feed real, no [] ."""
    from cores.opportunity.adapters.opire import OpyreAdapter

    seen: list[str] = []
    _fake_httpx(monkeypatch, seen)

    opps = _run(OpyreAdapter({}).fetch_opportunities())

    assert seen == ["https://api.opire.dev/rewards"]
    assert len(opps) == 3
    assert all(o.platform == "opyre" for o in opps)
    assert opps[0].id.startswith("opyre_")


def test_microtask_filters_by_effort_and_reward(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pulse cycle: solo tareas cortas con recompensa que valga el envío."""
    from cores.opportunity.adapters.opire import OpyreMicrotaskAdapter

    _fake_httpx(monkeypatch, [])

    opps = _run(OpyreMicrotaskAdapter({}).fetch_opportunities())

    # 01R1: $100 / 2h → entra. 01R2: $42 / 8h → esfuerzo alto, fuera.
    # 01R3: $0 / 6h (default) → recompensa bajo el mínimo, fuera.
    assert len(opps) == 1
    assert opps[0].reward == 100.0
    assert opps[0].effort_hours == 2.0
    assert all(o.platform == "opyre_microtask" for o in opps)


def test_dead_network_degrades_to_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fallo de red no debe explotar: degrada a lista vacía."""

    class Dead:
        def __init__(self, *a: Any, **kw: Any) -> None:
            pass

        async def __aenter__(self) -> Dead:
            raise ConnectionError()

        async def __aexit__(self, *a: Any) -> None:
            pass

    monkeypatch.setattr("httpx.AsyncClient", Dead)

    from cores.opportunity.adapters.opire import OpireAdapter

    assert _run(OpireAdapter({}).fetch_opportunities()) == []
