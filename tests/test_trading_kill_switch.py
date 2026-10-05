"""Kill switch: tiene que existir, persistir y BLOQUEAR de verdad.

Por qué existe este archivo (auditoría 2026-10-05):

1. **Bypass.** `api/routers/trading.py:504` llamaba `kill.is_triggered(...)`,
   un método que **nunca existió** (`KillSwitchManager` sólo tiene
   `is_active`). El `AttributeError` caía en `except Exception: pass`, así que
   el path de compra real (`POST /api/trading/pump/execute`) **nunca
   chekeaba el kill switch**. Un control que se puede saltear por un typo no
   es un control.

2. **No persistía.** `KillSwitchManager` era RAM por instancia. Cada call site
   creaba el suyo (`trading.py`, `memecoin_paper.py`, `RiskEngine`), así que
   el switch que activaba el paper loop era un objeto **distinto** del que
   consultaba el path de compra. Y un restart lo borraba.

Estos tests fijan el comportamiento correcto. El de persistencia usa un
`TradingStore` con `data_dir` temporal: nunca toca `data/trading/` real.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from cores.trading.risk import KillSwitchLevel, KillSwitchManager
from cores.trading.store import TradingStore


@pytest.fixture
def store() -> Iterator[TradingStore]:
    with tempfile.TemporaryDirectory() as tmp:
        yield TradingStore(data_dir=Path(tmp))


def test_activate_global_blocks(store: TradingStore) -> None:
    k = KillSwitchManager(store=store)
    assert k.is_active(KillSwitchLevel.GLOBAL) is False

    k.activate(KillSwitchLevel.GLOBAL, reason="test", triggered_by="human")

    assert k.is_active(KillSwitchLevel.GLOBAL) is True


def test_survives_a_new_instance(store: TradingStore) -> None:
    """El switch que activaste tiene que seguir activo en otra instancia.

    Esto es lo que fallaba: cada `KillSwitchManager()` nacía limpio.
    """
    KillSwitchManager(store=store).activate(KillSwitchLevel.GLOBAL, reason="broke", triggered_by="human")

    # Instancia completamente nueva, mismo store = mismo estado.
    fresh = KillSwitchManager(store=store)
    assert fresh.is_active(KillSwitchLevel.GLOBAL) is True


def test_deactivate_requires_human_and_persists(store: TradingStore) -> None:
    k = KillSwitchManager(store=store)
    k.activate(KillSwitchLevel.GLOBAL, reason="x", triggered_by="human")

    # Un trigger automático NO puede desactivar.
    assert k.deactivate(KillSwitchLevel.GLOBAL, triggered_by="system") is False
    assert KillSwitchManager(store=store).is_active(KillSwitchLevel.GLOBAL) is True

    # Sólo un humano.
    assert k.deactivate(KillSwitchLevel.GLOBAL, triggered_by="human") is True
    assert KillSwitchManager(store=store).is_active(KillSwitchLevel.GLOBAL) is False


def test_strategy_level_persists_by_identifier(store: TradingStore) -> None:
    k = KillSwitchManager(store=store)
    k.activate(KillSwitchLevel.STRATEGY, reason="bad strat", affected=["pump_v1"], triggered_by="human")

    fresh = KillSwitchManager(store=store)
    assert fresh.is_active(KillSwitchLevel.STRATEGY, "pump_v1") is True
    assert fresh.is_active(KillSwitchLevel.STRATEGY, "otra") is False


def test_is_active_is_the_real_method(store: TradingStore) -> None:
    """Guard contra la regresión exacta: `is_triggered` no existe.

    Si alguien reintroduce el typo, el import/call del endpoint vuelve a
    lanzar AttributeError — y este test lo documenta.
    """
    k = KillSwitchManager(store=store)
    assert hasattr(k, "is_active")
    assert not hasattr(k, "is_triggered"), "is_triggered no debe volver: el endpoint usa is_active"


def test_sin_store_no_rompe(store: TradingStore) -> None:
    """El modo RAM (sin store) debe seguir funcionando, por si acaso."""
    k = KillSwitchManager()
    assert k.is_active(KillSwitchLevel.GLOBAL) is False
    k.activate(KillSwitchLevel.GLOBAL, reason="x", triggered_by="human")
    assert k.is_active(KillSwitchLevel.GLOBAL) is True


# ── El bypass, probado sobre el endpoint REAL ──────────────────
#
# El test de arriba verifica que `is_active` existe y que el estado
# persiste. Eso NO alcanza: el bug original no estaba en risk.py sino en el
# endpoint, que llamaba un método inexistente dentro de un
# `except Exception: pass`. Un test de la clase no habría caído nunca.
#
# Estos tests ejecutan `pump_execute` de verdad y comprueban que el kill
# switch ACTIVO bloquea la compra (HTTP 423). Si alguien reintroduce el
# `is_triggered` + `except: pass`, estos tests caen.


@pytest.fixture
def live_client(monkeypatch, store: TradingStore):
    """Cliente con TRADING_MODE=real y approval válido, listo para /pump/execute."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import api.routers.trading as trading_router
    from cores.trading.risk import KillSwitchLevel, KillSwitchManager

    # REAL mode: sin esto el endpoint corta en 412 antes del kill switch.
    monkeypatch.setenv("TRADING_MODE", "real")
    # El endpoint hace `from cores.trading.store import TradingStore` DENTRO de
    # la funcion, asi que hay que patchear el atributo en el modulo ORIGEN.
    import cores.trading.store as store_mod

    monkeypatch.setattr(store_mod, "TradingStore", lambda *a, **k: store)

    app = FastAPI()
    app.include_router(trading_router.router)
    return TestClient(app), KillSwitchManager, KillSwitchLevel, store


def test_pump_execute_bloqueado_por_kill_switch_global(live_client, monkeypatch) -> None:
    """Kill switch global activo ⇒ 423, sin llegar a la compra."""

    client, mgr, level, store = live_client
    mgr(store=store).activate(level.GLOBAL, reason="test", triggered_by="human")

    # Approval válido para pasar la puerta anterior al kill switch.
    monkeypatch.setattr(trading_module(), "consume_approval", lambda *a, **k: True)

    r = client.post(
        "/api/trading/pump/execute",
        json={"mint": "So11111111111111111111111111111111111111112", "approval_token": "t", "amount_sol": 0.01},
    )
    assert r.status_code == 423, f"kill switch activo debe cortar con 423, no {r.status_code}: {r.text[:200]}"
    assert "kill switch" in r.json()["detail"]


def test_pump_execute_bloqueado_por_kill_switch_de_estrategia(live_client, monkeypatch) -> None:
    """Kill switch de estrategia también bloquea."""
    client, mgr, level, store = live_client
    mgr(store=store).activate(level.STRATEGY, reason="test", affected=["pump"], triggered_by="human")

    monkeypatch.setattr(trading_module(), "consume_approval", lambda *a, **k: True)

    r = client.post(
        "/api/trading/pump/execute",
        json={"mint": "So11111111111111111111111111111111111111112", "approval_token": "t", "amount_sol": 0.01},
    )
    assert r.status_code == 423


def test_sin_kill_switch_pasa_de_gate(live_client, monkeypatch) -> None:
    """Control: sin kill switch NO cortamos con 423 (el fallo real es otro)."""
    client, mgr, level, store = live_client
    assert mgr(store=store).is_active(level.GLOBAL) is False

    monkeypatch.setattr(trading_module(), "consume_approval", lambda *a, **k: True)
    # Cortamos antes de la compra real (adapter inexistente) para no tocar red.
    monkeypatch.setattr(
        trading_module(),
        "get_memecoin_adapter",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("stop-before-live")),
        raising=False,
    )

    r = client.post(
        "/api/trading/pump/execute",
        json={"mint": "So11111111111111111111111111111111111111112", "approval_token": "t", "amount_sol": 0.01},
    )
    assert r.status_code != 423, "sin kill switch no debe cortar con 423"


def trading_module():
    import api.routers.trading as m

    return m
