"""`doctor()["overall"]` tiene que poder empeorar.

Por qué existe: el aggregate era `healthy if healthy else unhealthy`. Eso
decía **"healthy" con 1 de 10 providers vivo**, porque sólo comprobaba que la
lista de healthy no estuviera vacía. No distinguía "todo bien" de "hay al
menos uno". Medido en vivo (2026-10-05): 4/10 sana y el endpoint reportaba
`overall: healthy`.

Es la misma clase de fallo que cerramos en #48 (UNKNOWN renderizado como $0)
y en el panel de /ai: un indicador que no puede empeorar no es un indicador,
es un eco. Un self-diagnostic que sólo dice "bien" mientras 6 providers están
caídos hace perder tiempo al owner.
"""

from __future__ import annotations

from typing import Any

import pytest

from cores.ai.runtime import OAR
from cores.ai.runtime.interfaces import OARConfig


class _FakeHealth:
    """HealthMonitor stub con conteos fijos."""

    def __init__(self, healthy: list[str], degraded: list[str], unhealthy: list[str]):
        self._healthy = healthy
        self._degraded = degraded
        self._unhealthy = unhealthy

    def get_healthy_providers(self) -> list[str]:
        return self._healthy

    def get_degraded_providers(self) -> list[str]:
        return self._degraded

    def get_unhealthy_providers(self) -> list[str]:
        return self._unhealthy

    def get_all_health(self) -> dict[str, Any]:
        return {}

    def get_healthy_count(self) -> int:
        return len(self._healthy)


@pytest.fixture
def oar_with(monkeypatch):
    def _make(healthy: list[str], degraded: list[str], unhealthy: list[str]) -> OAR:
        oar = OAR(OARConfig(enabled_providers=["ollama"]))
        oar._initialized = True
        oar._health = _FakeHealth(healthy, degraded, unhealthy)  # type: ignore[assignment]
        return oar

    return _make


def test_all_healthy_is_healthy(oar_with):
    d = oar_with(["a", "b"], [], []).doctor()
    assert d["overall"] == "healthy"
    assert d["providers"]["usable"] == 2


def test_degraded_provider_still_counts_as_overall_healthy(oar_with):
    """Un provider degradado sigue aportando; no es motivo de alarma global."""
    d = oar_with(["a"], ["b"], []).doctor()
    assert d["overall"] == "healthy"


def test_most_dead_is_degraded_not_healthy(oar_with):
    """El caso que fallaba: 4 sanas, 6 muertas ⇒ NO 'healthy'."""
    d = oar_with(["a", "b", "c", "d"], [], ["e", "f", "g", "h", "i", "j"]).doctor()
    assert d["overall"] == "degraded"
    assert d["providers"]["usable"] == 4
    assert d["providers"]["total"] == 10


def test_one_out_of_ten_is_degraded(oar_with):
    """1 sana de 10 no es 'healthy'. Ese era exactamente el bug."""
    d = oar_with(["only"], [], [f"dead{i}" for i in range(9)]).doctor()
    assert d["overall"] == "degraded"
    assert d["providers"]["usable"] == 1


def test_all_dead_is_unhealthy(oar_with):
    d = oar_with([], [], ["a", "b"]).doctor()
    assert d["overall"] == "unhealthy"
    assert d["providers"]["usable"] == 0


def test_none_registered_is_unknown_not_unhealthy(oar_with):
    """Sin providers registrados no sabemos nada: UNKNOWN, no VERDICT."""
    d = oar_with([], [], []).doctor()
    assert d["overall"] == "unknown"
    assert d["providers"]["total"] == 0


def test_not_initialized_still_errors(oar_with):
    oar = OAR(OARConfig(enabled_providers=["ollama"]))
    oar._initialized = False
    assert "error" in oar.doctor()
