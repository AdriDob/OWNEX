"""Trading quality gates — pinean los fixes 2026-09-17 (sesión trading máximo).

1. Ningún job de trading/investment apunta a un handler inexistente (los 14
   lifecycle muertos con args=[] se eliminaron; precedente 2026-09-09).
2. El router /api/trading se monta UNA vez (el doble-mount duplicaba rutas).
3. execute_trade (arbitraje real) es fail-closed sin allow_live explícito.
4. risk_guardian_check corre el chequeo real y nunca rompe el tick.
"""

from __future__ import annotations

import importlib
import os

os.environ["CATEYE_CSRF_DISABLED"] = "1"

_LIFECYCLE_BARE = (
    "cores.trading.lifecycle:start_backtest",
    "cores.trading.lifecycle:complete_backtest",
    "cores.trading.lifecycle:start_canary",
    "cores.trading.lifecycle:start_live",
    "cores.trading.lifecycle:complete_validation",
    "cores.trading.lifecycle:start_paper_trading",
)


def _trading_jobs():
    from cores.scheduler.jobs import get_all_jobs

    jobs = get_all_jobs()
    return [j for cycle in ("trading", "investment") for j in jobs.get(cycle, [])]


def test_no_dead_lifecycle_handlers():
    """Ningún job vivo referencia los handlers lifecycle inexistentes."""
    for job in _trading_jobs():
        assert job.handler not in _LIFECYCLE_BARE, f"job muerto: {job.job_id}"


def test_all_trading_job_handlers_resolve():
    """Todo handler registrado resuelve a callable (regla 2026-09-09)."""
    for job in _trading_jobs():
        handler = str(job.handler)  # en runtime los handlers son "modulo:attr"
        mod_name, _, attr = handler.partition(":")
        assert attr, f"handler sin attr: {job.job_id}"
        module = importlib.import_module(mod_name)
        assert callable(getattr(module, attr, None)), f"no resuelve: {handler}"


def test_trading_router_mounted_once():
    """GET /api/trading/overview existe exactamente 1 vez (no doble-mount)."""
    import api.main as m

    paths = [getattr(r, "path", "") for r in m.app.routes]
    assert paths.count("/api/trading/overview") == 1


async def test_execute_trade_blocked_by_default():
    """Sin allow_live explícito, execute_trade raisea antes de tocar ccxt."""
    from cores.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter

    adapter = GlobalArbitrageAdapter(config={})
    assert adapter._allow_live is False
    with __import__("pytest").raises(RuntimeError, match="allow_live=False"):
        await adapter.execute_trade({"buy_on": "kraken", "sell_on": "coinbase"})


def test_execute_trade_flag_opt_in_stored():
    """allow_live=True queda guardado (el camino live sigue existiendo)."""
    from cores.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter

    assert GlobalArbitrageAdapter(config={"allow_live": True})._allow_live is True


def test_risk_guardian_runner_returns_honest_summary():
    """El runner devuelve el chequeo real (checked=0 honesto sin estrategias)."""
    from cores.investment.risk_guardian import run_risk_guardian_check

    result = run_risk_guardian_check()
    for key in ("checked", "paused", "resumed", "warnings", "healthy"):
        assert key in result


def test_risk_guardian_runner_never_raises(monkeypatch):
    """Si el guardian explota, el tick sobrevive con error honesto."""
    import cores.investment.risk_guardian as rg

    def _boom():
        raise ValueError("db caída")

    monkeypatch.setattr(rg, "get_risk_guardian", _boom)
    result = rg.run_risk_guardian_check()
    assert result["checked"] == 0
    assert "db caída" in result["error"]
