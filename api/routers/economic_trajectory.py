"""Economic Trajectory API — REAL / PIPELINE / SCENARIO en una llamada.

El frontend responde en segundos (spec §38): cuánto cobré, cuánto trabajé,
cuál es mi $/hora, qué canal funciona, cuánto falta para el objetivo.

Best-effort por sección: si el RevenueTracker falla, REAL vuelve vacío con
``source_error`` — nunca 500, nunca 0 inventado como tasa.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/economic-trajectory", tags=["economic-trajectory"])


def _opportunities() -> tuple[list[Any], str | None]:
    """Lee el SSOT de caja (RevenueTracker). Devuelve (opps, error|None)."""
    try:
        from cores.revenue_tracker.revenue_tracker import get_revenue_tracker

        return list(get_revenue_tracker().opportunities.values()), None
    except Exception as exc:  # noqa: BLE001 — degradado, nunca 500
        return [], f"revenue_tracker unavailable: {exc}"


def _available_hours() -> float:
    """Capacidad configurada (spec §2). Prioriza la del mission hub si existe."""
    try:
        from api.routers.mission_hub import _load_state

        value = float(_load_state().get("available_hours_per_week") or 0)
        if value > 0:
            return value
    except Exception:  # noqa: BLE001
        pass
    return 77.0


@router.get("/trajectory")
async def economic_trajectory(
    hours_d90: float = Query(0.0, ge=0.0, le=10000.0),
    hours_d180: float = Query(0.0, ge=0.0, le=10000.0),
    hours_d365: float = Query(0.0, ge=0.0, le=10000.0),
) -> dict[str, Any]:
    """Trayectoria completa: REAL / PIPELINE / SCENARIO + calibración + canales."""
    from cores.economic_trajectory.trajectory import build_trajectory

    opps, err = _opportunities()
    traj = build_trajectory(
        opps,
        hours_by_period={"d90": hours_d90, "d180": hours_d180, "d365": hours_d365},
        available_hours_per_week=_available_hours(),
    )
    out = traj.to_dict()
    out["source_error"] = err
    return out


@router.get("/gap")
async def economic_gap(
    target_monthly: float = Query(..., gt=0.0, le=10_000_000.0),
) -> dict[str, Any]:
    """Gap a objetivo: TARGET - REALIZED - VERIFIABLE_PENDING (nunca potencial)."""
    from cores.economic_trajectory.trajectory import gap_to_target

    opps, err = _opportunities()
    rows = [
        {
            "revenue_state": getattr(o, "revenue_state", ""),
            "amount": getattr(o, "amount", 0.0),
        }
        for o in opps
    ]
    realized = sum(float(r["amount"] or 0) for r in rows if str(r["revenue_state"]).lower() in ("paid", "net"))
    pending = sum(
        float(r["amount"] or 0) for r in rows if str(r["revenue_state"]).lower() in ("submitted", "accepted", "awarded")
    )
    out = gap_to_target(target_monthly, realized, pending, _available_hours())
    out["source_error"] = err
    return out


@router.get("/scenarios")
async def economic_scenarios(
    tier: str = Query("central"),
    horizon: str = Query("m1_3"),
) -> dict[str, Any]:
    """Escenarios de planificación + comparación con lo REAL. Nunca forecast."""
    from cores.economic_trajectory.trajectory import (
        compare_scenario_to_real,
        scenarios_block,
    )

    opps, err = _opportunities()
    realized = sum(
        float(getattr(o, "amount", 0.0) or 0)
        for o in opps
        if str(getattr(o, "revenue_state", "")).lower() in ("paid", "net")
    )
    return {
        "scenarios": scenarios_block(),
        "comparison": compare_scenario_to_real(realized, tier=tier, horizon=horizon),
        "realized_measured": round(realized, 2),
        "source_error": err,
    }
