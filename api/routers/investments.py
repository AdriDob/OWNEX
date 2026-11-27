"""API endpoints for the OWNEX Investment Engine."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/investment", tags=["investment"])

_investment_manager = None
_investment_metrics = None
_alloc_ctrl = None


def _get_manager():
    global _investment_manager
    if _investment_manager is None:
        from ownex_investment_engine.manager import get_investment_manager as _gm

        _investment_manager = _gm()
    return _investment_manager


def _get_metrics():
    global _investment_metrics
    if _investment_metrics is None:
        from ownex_investment_engine.metrics import get_investment_metrics as _gm

        _investment_metrics = _gm()
    return _investment_metrics


def _get_alloc():
    global _alloc_ctrl
    if _alloc_ctrl is None:
        from ownex_investment_engine.allocation import get_allocation_controller as _ac

        _alloc_ctrl = _ac()
    return _alloc_ctrl
