"""Capital API Router — endpoints for capital management features."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.capital.allocation import get_allocation_engine
from cores.capital.diversification import get_diversification_engine
from cores.capital.forecasting import get_forecasting_engine
from cores.capital.risk import get_risk_engine
from cores.capital.runway import get_runway_engine

logger = logging.getLogger("ownex.api.capital")

router = APIRouter(prefix="/api/capital", tags=["capital"])


class RunwayRequest(BaseModel):
    work_income_usd_per_month: float = 0
    savings_usd_per_month: float = 0
    start_capital_usd: float = 0
    annual_return_rate: float = 0.10
    target_monthly_usd: float = 100000


class RiskAssessmentRequest(BaseModel):
    capital_usd: float = 0
    income_sources: list[dict] = []
    platform_exposure: dict[str, float] = {}


class AllocationRequest(BaseModel):
    available_capital: float
    runway_months: float
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive
    income_stability: str = "moderate"  # low, moderate, high
    goals: list[str] = []


class ForecastingRequest(BaseModel):
    work_income_usd_per_month: float
    savings_usd_per_month: float
    start_capital_usd: float
    annual_return_rate: float = 0.10
    target_monthly_usd: float = 100000
    horizon_months: int = 12


class DiversificationRequest(BaseModel):
    income_sources: list[dict] = []
    platform_exposure: dict[str, float] = {}


@router.get("/runway")
def get_runway() -> dict[str, Any]:
    """Get runway analysis based on current capital state."""
    try:
        engine = get_runway_engine()
        # For now, use defaults - in production would use request params
        result = engine.calculate_runway()
        return result
    except Exception as e:
        logger.exception("Runway calculation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/runway")
def calculate_runway(req: RunwayRequest) -> dict[str, Any]:
    """Calculate runway with custom parameters."""
    try:
        engine = get_runway_engine()
        result = engine.calculate_runway(
            work_income_usd_per_month=req.work_income_usd_per_month,
            savings_usd_per_month=req.savings_usd_per_month,
            start_capital_usd=req.start_capital_usd,
            annual_return_rate=req.annual_return_rate,
            target_monthly_usd=req.target_monthly_usd,
        )
        return result
    except Exception as e:
        logger.exception("Runway calculation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk")
def get_risk() -> dict[str, Any]:
    """Get current risk assessment."""
    try:
        engine = get_risk_engine()
        result = engine.assess_risk()
        return result
    except Exception as e:
        logger.exception("Risk assessment failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk")
def assess_risk(req: RiskAssessmentRequest) -> dict[str, Any]:
    """Assess risk with custom parameters."""
    try:
        engine = get_risk_engine()
        result = engine.assess_risk(
            capital_usd=req.capital_usd,
            income_sources=req.income_sources,
            platform_exposure=req.platform_exposure,
        )
        return result
    except Exception as e:
        logger.exception("Risk assessment failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allocation")
def get_allocation() -> dict[str, Any]:
    """Get capital allocation recommendations."""
    try:
        engine = get_allocation_engine()
        result = engine.recommend_allocation()
        return result
    except Exception as e:
        logger.exception("Allocation recommendation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/allocation")
def recommend_allocation(req: AllocationRequest) -> dict[str, Any]:
    """Get capital allocation recommendations with custom parameters."""
    try:
        engine = get_allocation_engine()
        result = engine.recommend_allocation(
            available_capital=req.available_capital,
            runway_months=req.runway_months,
            risk_tolerance=req.risk_tolerance,
            income_stability=req.income_stability,
            goals=req.goals,
        )
        return result
    except Exception as e:
        logger.exception("Allocation recommendation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecasting")
def get_forecasting() -> dict[str, Any]:
    """Get capital forecasting (P10/P50/P90)."""
    try:
        engine = get_forecasting_engine()
        result = engine.forecast()
        return result
    except Exception as e:
        logger.exception("Forecasting failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forecasting")
def forecast_capital(req: ForecastingRequest) -> dict[str, Any]:
    """Forecast capital with custom parameters."""
    try:
        engine = get_forecasting_engine()
        result = engine.forecast(
            work_income_usd_per_month=req.work_income_usd_per_month,
            savings_usd_per_month=req.savings_usd_per_month,
            start_capital_usd=req.start_capital_usd,
            annual_return_rate=req.annual_return_rate,
            target_monthly_usd=req.target_monthly_usd,
            horizon_months=req.horizon_months,
        )
        return result
    except Exception as e:
        logger.exception("Forecasting failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diversification")
def get_diversification() -> dict[str, Any]:
    """Get income diversification analysis."""
    try:
        engine = get_diversification_engine()
        result = engine.analyze()
        return result
    except Exception as e:
        logger.exception("Diversification analysis failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diversification")
def analyze_diversification(req: DiversificationRequest) -> dict[str, Any]:
    """Analyze income diversification with custom parameters."""
    try:
        engine = get_diversification_engine()
        result = engine.analyze(
            income_sources=req.income_sources,
            platform_exposure=req.platform_exposure,
        )
        return result
    except Exception as e:
        logger.exception("Diversification analysis failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot")
def capital_snapshot() -> dict[str, Any]:
    """Unified capital snapshot — single source of truth for all money."""
    from api.routers.financial_truth import capital_snapshot as financial_capital_snapshot

    return financial_capital_snapshot()
