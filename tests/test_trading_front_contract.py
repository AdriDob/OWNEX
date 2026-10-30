"""Trading front contract — el router accionable montado + endpoint /overview honesto.

Diagnóstico (2026-09-15): api/routers/trading.py (copy/masters/ingest/advisor/
approve) vivía SIN montar en api/main — el front consumía un contrato
inexistente (total_value/pnl/positions) y el dashboard siempre mostraba 0.
Estos tests pinean el contrato REAL que el front consume.
"""

from __future__ import annotations

import os

os.environ["CATEYE_CSRF_DISABLED"] = "1"


def _authed_client() -> tuple:
    from fastapi.testclient import TestClient

    import api.main as m

    client = TestClient(m.app)
    login = client.post("/api/auth/login", json={"device_id": "trading-contract-test"}).json()
    token = login["data"]["token"]
    return client, {"Authorization": f"Bearer {token}"}


def test_trading_router_mounted_and_accionable() -> None:
    """El router accionable existe montado en main (regresión del bug)."""
    client, headers = _authed_client()
    r = client.get("/api/trading/dashboard/summary", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "copy" in body and "reasoning" in body
    assert body["copy"]["mode"] == "DRY_RUN"


def test_overview_honest_contract() -> None:
    client, headers = _authed_client()
    r = client.get("/api/trading/overview", headers=headers)
    assert r.status_code == 200
    body = r.json()
    # modo honesto: nunca inventa LIVE
    assert body["mode"] in ("dry_run", "paper_trading", "real")
    assert body["is_live"] is False or body["mode"] == "real"
    assert isinstance(body["is_simulation"], bool)
    # automatización visible
    assert body["jobs"]["total"] >= 1
    assert body["jobs"]["enabled"] <= body["jobs"]["total"]
    # métricas paper: NO_DATA honesto sin trades, nunca ceros inventados
    assert body["metrics"]["verdict"] in ("NO_DATA", "EDGE_CANDIDATE", "NO_EDGE")
    if body["metrics"]["trade_count"] == 0:
        assert body["metrics"]["win_rate"] is None
        assert body["metrics"]["profit_factor"] is None
    # config pendiente expuesta (DRY_RUN → al menos trading_live manual)
    ids = {p["id"] for p in body["pending_config"]}
    assert "trading_live" in ids
    # claves que el front usa están presentes
    for key in ("mode_label", "emergency_stop", "copy", "masters", "reasoning", "generated_at"):
        assert key in body


def test_action_endpoints_mounted() -> None:
    """Acciones fáciles del front: toggle, emergency-stop, approve/reject."""
    client, headers = _authed_client()
    assert client.post("/api/trading/reasoning/approve/nope", headers=headers).status_code in (200, 404)
    assert client.post("/api/trading/reasoning/reject/nope", headers=headers).status_code in (200, 404)
    assert (
        client.post("/api/trading/copy/emergency-stop", json={"reason": "contract test"}, headers=headers).status_code
        == 200
    )
    assert client.post("/api/trading/copy/release", headers=headers).status_code == 200


def test_metrics_history_ok() -> None:
    client, headers = _authed_client()
    r = client.get("/api/trading/metrics/history", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "metrics" in body
    assert "trade_count" in body["metrics"] or "trades" in body["metrics"]
