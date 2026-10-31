"""MT5 Bridge API router — minimal, read-only-ish behind feature flag.

Endpoints:
  GET /api/trading/mt5/status    → bridge health + state
  POST /api/trading/mt5/arm      → arm with limits + TTL
  POST /api/trading/mt5/disarm   → block new orders
  POST /api/trading/mt5/kill     → hard kill
  GET /api/trading/mt5/positions → open positions
  GET /api/trading/mt5/pnl       → PnL día/sesión

Security:
  - TRADING_MODE must NOT be "real" default (guards prevent live orders).
  - All orders gated by arm session + risk checks.
  - Bridge credentials ONLY on the Windows sidecar host.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from cores.trading.mt5 import bridge_client, session
from cores.trading.mt5 import risk as mt5_risk

router = APIRouter(prefix="/api/trading/mt5", tags=["mt5-bridge"])

# ---------------------------------------------------------------------------
# Helper: guard that TRADING_MODE ≠ "real" in this deployment
# ---------------------------------------------------------------------------


def _check_mode() -> None:

    if __import__("os").getenv("TRADING_MODE", "paper") == "real":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MT5 bridge disabled in real mode",
        )


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


@router.get("/status")
async def status_endpoint() -> Any:
    _check_mode()
    return bridge_client.get_status()


# ---------------------------------------------------------------------------
# Arm
# ---------------------------------------------------------------------------


@router.post("/arm")
async def arm_endpoint(body: dict) -> Any:
    _check_mode()
    session.set_session(body)
    result = bridge_client.arm_session(body)
    return {"session": session.get_session().to_dict() if session.get_session() else None, **result}


# ---------------------------------------------------------------------------
# Disarm
# ---------------------------------------------------------------------------


@router.post("/disarm")
async def disarm_endpoint() -> Any:
    _check_mode()
    session.get_session().kill = True  # type: ignore
    bridge_client.disarm_session()
    return {"status": "disarmed"}


# ---------------------------------------------------------------------------
# Kill
# ---------------------------------------------------------------------------


@router.post("/kill")
async def kill_endpoint() -> Any:
    _check_mode()
    bridge_client.kill_session()
    return {"status": "killed"}


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------


@router.get("/positions")
async def positions_endpoint() -> Any:
    _check_mode()
    return bridge_client.get_positions()


# ---------------------------------------------------------------------------
# PnL
# ---------------------------------------------------------------------------


@router.get("/pnl")
async def pnl_endpoint() -> Any:
    _check_mode()
    return bridge_client.get_pnl()


# ---------------------------------------------------------------------------
# Order — solo si arm + risk OK (el bridge sidecar valida lo restante)
# ---------------------------------------------------------------------------


@router.post("/order")
async def order_endpoint(order: dict) -> Any:
    _check_mode()
    s = session.get_session()
    if s is None:
        raise HTTPException(status_code=403, detail="Session not armed")

    # Risk guards (mirroring bridge sidecar logic)
    lot = order.get("lot", 0)
    symbol = order.get("symbol", "")

    if not mt5_risk.lot_ok(lot, s.max_lot):
        raise HTTPException(status_code=400, detail="lot exceeds max")

    if not mt5_risk.symbol_ok(symbol, s.whitelist):
        raise HTTPException(status_code=400, detail="symbol not in whitelist")

    # Forward to bridge
    return bridge_client.send_order(order)
