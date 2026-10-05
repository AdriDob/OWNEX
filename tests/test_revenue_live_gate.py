"""Modo LIVE de revenue-multiplier exige Human Gate.

Por qué existe (auditoría 2026-10-05): `POST /api/revenue-multiplier/activate
{"mode":"live"}` llegaba a `_live_execute` → `RealExecutor.execute_order` →
`send_transaction` (broadcast on-chain) SIN:

- approval token
- chequeo del kill switch
- verificar `TradingConfig.is_live`

El único límite era `max_position_usd` (default 500 USD). Es decir: un POST
a un endpoint movía fondos reales. Se reusó el mismo gate que ya funciona en
`/api/trading/pump/execute` (`consume_approval`, HMAC single-use).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.routers.revenue_multiplier as rm_router


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(rm_router.router)
    return TestClient(app)


class TestLiveRequiresHumanGate:
    def test_live_sin_token_does_403(self, client: TestClient) -> None:
        """Sin token, LIVE no se ejecuta. Éste es el bug."""
        r = client.post("/api/revenue-multiplier/activate", json={"mode": "live"})
        assert r.status_code == 403, f"live sin token debe ser 403, dio {r.status_code}"
        assert "Human Gate" in r.json()["detail"]

    def test_live_con_token_invalido_does_403(self, client: TestClient) -> None:
        r = client.post("/api/revenue-multiplier/activate", json={"mode": "live", "approval_token": "basura"})
        assert r.status_code == 403

    def test_live_con_token_valido_pasa_el_gate(self, client: TestClient) -> None:
        """Control: el gate deja pasar cuando el token ES válido.

        Verifica que el 403 no sea un 'siempre 403' que ni bloquea ni deja
        operar — tiene que haber un camino de operación con Human Gate.
        """
        from cores.automation.safety import issue_approval

        token = issue_approval(action="revenue_live_trade", target="max_revenue_live", workspace="revenue")

        with (
            patch.object(rm_router, "RevenueMultiplierOrchestrator", create=True) as mock_orch,
            patch("cores.automation.safety.consume_approval", return_value=True),
        ):
            mock_orch.return_value.activate_max_revenue_mode.return_value = {"ok": True}
            r = client.post(
                "/api/revenue-multiplier/activate",
                json={"mode": "live", "approval_token": token, "target": "max_revenue_live"},
            )

        # Llego al orchestrator (o fallo por otro motivo) pero NO por 403.
        assert r.status_code != 403, "un token válido no debe dar 403"

    def test_kill_switch_global_bloquea_live(self, client: TestClient) -> None:
        """Con el kill switch global prendido, live da 423 aunque haya token."""
        import tempfile
        from pathlib import Path

        from cores.trading.risk import KillSwitchLevel, KillSwitchManager
        from cores.trading.store import TradingStore

        with tempfile.TemporaryDirectory() as tmp:
            store = TradingStore(data_dir=Path(tmp))
            KillSwitchManager(store=store).activate(KillSwitchLevel.GLOBAL, reason="test", triggered_by="human")

            with (
                patch("cores.trading.store.TradingStore", lambda *a, **k: store),
                patch("cores.automation.safety.consume_approval", return_value=True),
            ):
                r = client.post(
                    "/api/revenue-multiplier/activate",
                    json={"mode": "live", "approval_token": "x", "target": "t"},
                )
        assert r.status_code == 423, f"kill switch debe dar 423, dio {r.status_code}"


class TestNonLiveUnaffected:
    def test_dry_run_no_exige_token(self, client: TestClient) -> None:
        """DRY_RUN es el default seguro: no debe exigir gate."""
        with patch.object(rm_router, "RevenueMultiplierOrchestrator", create=True) as mock_orch:
            mock_orch.return_value.activate_max_revenue_mode.return_value = {"ok": True}
            r = client.post("/api/revenue-multiplier/activate", json={"mode": "dry_run"})

        assert r.status_code != 403, "dry_run no debe pedir Human Gate"

    def test_paper_no_exige_token(self, client: TestClient) -> None:
        with patch.object(rm_router, "RevenueMultiplierOrchestrator", create=True) as mock_orch:
            mock_orch.return_value.activate_max_revenue_mode.return_value = {"ok": True}
            r = client.post("/api/revenue-multiplier/activate", json={"mode": "paper"})

        assert r.status_code != 403
