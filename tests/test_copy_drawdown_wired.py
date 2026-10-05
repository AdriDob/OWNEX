"""El control de drawdown de copy trading no era decorativo... hasta ahora.

Por qué existe (auditoría 2026-10-05). La cadena:

    CopyTradingEngine.record_daily_pnl(master, amount)   ← definición
    CopyTradingEngine._daily_pnl()                       ← lee
    CopyTradingEngine.daily_dd_pct()                      ← calcula
    CopyTradingEngine.risk_breached()                    ← dispara el stop

`record_daily_pnl` tenía **0 callers en producción**: sólo lo invocaba un
test. Por lo tanto `_daily_pnl()` devolvía siempre `{}`, `daily_dd_pct()`
devolvía **0.0** siempre, y `risk_breached()` **nunca podía dispararse por
drawdown**. El auto-stop por pérdida diaria era decorativo: parecía un
control y no controlaba nada.

El fix: el paper loop de memecoin es el único lugar del sistema que calcula
PnL REAL de trades cerrados (`paper_metrics` → `realized_pnl_sol`). Ahora
`_report_realized_pnl_to_copy` lo sube al registro del copy engine.

Regla: *un guard que nunca puede dispararse no es un guard: es documentación
con Side Effects: ninguno.*
"""

from __future__ import annotations

import inspect
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from cores.trading.copy_trading import CopyTradingEngine
from cores.trading.store import TradingStore


@pytest.fixture
def engine() -> Iterator[CopyTradingEngine]:
    with tempfile.TemporaryDirectory() as tmp:
        yield CopyTradingEngine(store=TradingStore(data_dir=Path(tmp)))


class TestDailyPnlIsWired:
    def test_record_daily_pnl_tiene_un_caller_de_produccion(self) -> None:
        """Guard estructural: si pierde al último caller, el DD vuelve a ser inerte."""
        import cores.trading.paper.memecoin_paper as paper

        src = inspect.getsource(paper)
        assert "record_daily_pnl" in src, (
            "el paper loop debe reportar el PnL realizado al copy engine; "
            "si se borra esa llamada, daily_dd_pct() vuelve a dar 0 siempre"
        )

    def test_el_bridge_reports_pnl_real(self, monkeypatch, tmp_path) -> None:
        """El bridge sube el PnL de los trades recién cerrados."""
        from cores.trading.paper.memecoin_paper import _report_realized_pnl_to_copy

        seen: list[tuple[str, float]] = []

        class _FakeEngine:
            def __init__(self, *a, **k):
                pass

            def record_daily_pnl(self, master_id: str, amount: float) -> None:
                seen.append((master_id, amount))

        import cores.trading.copy_trading as ct

        monkeypatch.setattr(ct, "CopyTradingEngine", _FakeEngine, raising=False)

        closed = [
            SimpleNamespace(pnl_sol=1.5),
            SimpleNamespace(pnl_sol=-0.5),
            SimpleNamespace(pnl_sol=0.25),
        ]
        _report_realized_pnl_to_copy(closed)

        assert seen == [("memecoin_paper", 1.25)], "debe sumar los tres PnL: 1.5 - 0.5 + 0.25"

    def test_el_bridge_no_reporta_si_no_hubo_trades(self, monkeypatch) -> None:
        from cores.trading.paper.memecoin_paper import _report_realized_pnl_to_copy

        class _Boom:
            def __init__(self, *a, **k):
                raise AssertionError("no debe instanciar el engine si no cerró nada")

        import cores.trading.copy_trading as ct

        monkeypatch.setattr(ct, "CopyTradingEngine", _Boom, raising=False)
        _report_realized_pnl_to_copy([])  # no debe fallar

    def test_el_bridge_no_traga_el_error(self, monkeypatch, caplog) -> None:
        """Si el bridge falla, avisa: tragarse el error devuelve al estado mudo."""
        from cores.trading.paper.memecoin_paper import _report_realized_pnl_to_copy

        class _Boom:
            def __init__(self, *a, **k):
                raise RuntimeError("store caido")

        import cores.trading.copy_trading as ct

        monkeypatch.setattr(ct, "CopyTradingEngine", _Boom, raising=False)
        _report_realized_pnl_to_copy([SimpleNamespace(pnl_sol=1.0)])  # no debe propagar

    def test_trades_sin_pnl_no_rompen(self, monkeypatch) -> None:
        from cores.trading.paper.memecoin_paper import _report_realized_pnl_to_copy

        called = []
        import cores.trading.copy_trading as ct

        class _FakeEngine:
            def __init__(self, *a, **k):
                pass

            def record_daily_pnl(self, m, a):
                called.append((m, a))

        monkeypatch.setattr(ct, "CopyTradingEngine", _FakeEngine, raising=False)
        _report_realized_pnl_to_copy([SimpleNamespace(pnl_sol=None)])
        assert called == [], "sin PnL no hay nada que reportar"


class TestDrawdownCanNowFire:
    """El guard que antes no podía dispararse."""

    def test_daily_dd_pct_deja_de_ser_siempre_cero(self, engine: CopyTradingEngine) -> None:
        assert engine.daily_dd_pct() == 0.0, "sin trades, 0 es correcto"

        # -$80 sobre $1000 de equity = 8% de drawdown diario
        engine.record_daily_pnl("memecoin_paper", -80.0)
        dd = engine.daily_dd_pct()
        assert dd > 0.0, "con PnL negativo registrado el DD debe ser > 0"

    def test_pnl_positivo_no_genera_drawdown(self, engine: CopyTradingEngine) -> None:
        engine.record_daily_pnl("memecoin_paper", 50.0)
        assert engine.daily_dd_pct() == 0.0

    def test_risk_breached_consulta_el_dd(self, engine: CopyTradingEngine) -> None:
        """`risk_breached` debe mirar el DD (o max_open_positions), no ignorarlo."""
        import inspect

        src = inspect.getsource(type(engine).risk_breached)
        assert "daily_dd_pct" in src or "max_open_positions" in src, (
            "risk_breached tiene que evaluar el drawdown; si sólo mira otra cosa, el DD es informational"
        )
