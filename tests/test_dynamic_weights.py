"""Tests: pesos dinámicos por evidencia de conversión."""

from __future__ import annotations

from cores.direct_work_engine.dynamic_weights import (
    MAX_WEIGHT,
    MIN_WEIGHT,
    compute_dynamic_weights,
)


def test_arranque_sin_evidencia_es_caja_rapida() -> None:
    w = compute_dynamic_weights([])
    assert w["fast_cash"] == 0.8
    assert w["security_upside"] == 0.2


def test_security_hit_fuerte_migra_pesos() -> None:
    ev = [{"category": "bug_bounty", "accepted": True, "hours": 8, "ev_usd": 4000}]
    w = compute_dynamic_weights(ev)
    assert w["security_upside"] > w["fast_cash"]


def test_bounds_nunca_ciego() -> None:
    ev = [
        {"category": "bug_bounty", "accepted": True, "hours": 2, "ev_usd": 50_000},
        {"category": "ai_evaluation", "accepted": True, "hours": 10, "ev_usd": 120},
    ]
    w = compute_dynamic_weights(ev)
    assert MIN_WEIGHT <= w["fast_cash"] <= MAX_WEIGHT
    assert MIN_WEIGHT <= w["security_upside"] <= MAX_WEIGHT


def test_unknown_o_sin_horas_no_suma_senal() -> None:
    before = compute_dynamic_weights([])
    ev = [
        {"category": "bug_bounty", "accepted": True},  # sin hours/ev
        {"category": "dev_bounty", "accepted": False, "hours": 5, "ev_usd": 100},
    ]
    assert compute_dynamic_weights(ev) == before


def test_fast_cash_hit_reequilibra() -> None:
    ev = [
        {"category": "bug_bounty", "accepted": True, "hours": 8, "ev_usd": 4000},
        {"category": "ai_evaluation", "accepted": True, "hours": 6, "ev_usd": 900},
        {"category": "dev_bounty", "accepted": True, "hours": 4, "ev_usd": 600},
    ]
    w = compute_dynamic_weights(ev)
    # fast-cash razonable recupera terreno sin borrar la señal de security
    assert w["fast_cash"] > MIN_WEIGHT
