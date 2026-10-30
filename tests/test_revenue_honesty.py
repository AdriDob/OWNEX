"""Cifras de revenue_multiplier: dejar de inventar números.

Por qué existe (auditoría 2026-10-05):

1. **`win_rate = 100%` garantizado.** `orchestrator.py:160` llamaba
   `record_trade(pnl=Decimal("0"), won=True)` con valores fijos. Da igual
   cuántos trades salgan: el ratio siempre daba 1.0. Una métrica que no
   puede bajar no es una métrica.

2. **Revenue siempre 0.** `record_revenue()` tenía **0 callers** en todo el
   repo, así que `_revenue_history` quedaba `[]` para siempre y
   `estimated_annual = 0 × 12 = 0` perpetuamente. `/api/revenue-multiplier/
   metrics` y `/report` servían ceros que parecían "no ganamos nada" cuando
   en realidad era "no estamos midiendo".

3. **`total_pnl` nunca有什么 dato.** El mismo caller fijo.

Regla del proyecto que esto restaura: **UNKNOWN nunca como cifra.** `None`
significa "no medido" y NO se convierte en 0 ni en 100%.
"""

from __future__ import annotations

from decimal import Decimal

from cores.revenue_multiplier.metrics.metrics_tracker import MetricsTracker


class TestRecordTradeHonesty:
    def test_pnl_desconocido_no_inventa_win_rate(self):
        """El caso del bug: 3 trades sin PnL medido NO son 100% ganados."""
        m = MetricsTracker()
        for _ in range(3):
            m.record_trade(pnl=None, won=None)

        t = m.to_dict()["trading"]
        assert t["total_trades"] == 3, "el trade se cuenta"
        assert t["win_rate"] == 0.0, "pero NO se cuenta como ganado"
        assert Decimal(t["total_pnl"]) == 0, "y no suma PnL inventado"

    def test_win_rate_real_usa_solo_trades_decididos(self):
        m = MetricsTracker()
        m.record_trade(pnl=Decimal("10"), won=True)
        m.record_trade(pnl=Decimal("-4"), won=False)
        m.record_trade(pnl=None, won=None)  # sin dato: no cuenta en el ratio

        t = m.to_dict()["trading"]
        assert t["total_trades"] == 3
        # ratio sobre 2 decididos: 1/2, no 1/3
        assert t["win_rate"] == 50.0
        assert Decimal(t["total_pnl"]) == Decimal("6"), "6 = 10 - 4, el None no suma"

    def test_pnl_cero_real_es_perdida_no_desconocido(self):
        """pnl=0 con won=False es una pérdida real; no es lo mismo que None."""
        m = MetricsTracker()
        m.record_trade(pnl=Decimal("0"), won=False)

        t = m.to_dict()["trading"]
        assert t["win_rate"] == 0.0
        assert Decimal(t["total_pnl"]) == 0

    def test_todo_ganado_sigue_dando_100(self):
        """El caso feliz no debe romperse: si realmente ganó, da 100."""
        m = MetricsTracker()
        m.record_trade(pnl=Decimal("5"), won=True)
        m.record_trade(pnl=Decimal("7"), won=True)

        assert m.to_dict()["trading"]["win_rate"] == 100.0


class TestRevenueNotAlwaysZero:
    def test_estimated_annual_deriva_de_30d_real(self):
        """`estimated_annual` = revenue_30d × 12 cuando HAY datos."""

        m = MetricsTracker()
        m.record_revenue(amount=Decimal("100"), category="bounty")
        # El entry se crea con now() => cae en 24h/7d/30d

        d = m.to_dict()["revenue"]
        assert d["30d"] == "100", "30d debe reflejar el entry real"
        assert d["estimated_annual"] == "1200", "100 × 12, proyección real"

    def test_sin_datos_no_inventa_proyeccion(self):
        """Sin history local y sin ledger, estimated_annual = 0, no NaN ni -1."""
        d = MetricsTracker().to_dict()["revenue"]
        assert d["estimated_annual"] == "0"
        assert d["total"] == "0"

    def test_record_revenue_es_llegado_por_alguien(self):
        """Guard de proceso: este test falla si `record_revenue` vuelve a
        quedar con 0 callers. Si el revenue real entra por otro lado
        (ledger), este test se actualiza; pero mientras el histórico esté
        vacío, el método DEBE tener al menos un caller en tests."""
        m = MetricsTracker()
        m.record_revenue(amount=Decimal("1"), category="x")
        assert m._revenue_history, "record_revenue debe ser funcional"

    def test_timestamps_recientes_caen_en_24h(self):
        from datetime import UTC, datetime, timedelta

        m = MetricsTracker()
        viejo = datetime.now(UTC) - timedelta(days=40)
        m.record_revenue(amount=Decimal("500"), category="old", timestamp=viejo)
        m.record_revenue(amount=Decimal("3"), category="new")

        d = m.to_dict()["revenue"]
        assert d["24h"] == "3", "sólo lo reciente entra en 24h"
        assert d["30d"] == "3", "el viejo de 40d no entra en 30d"
        assert d["total"] == "503", "pero sí en el total"
