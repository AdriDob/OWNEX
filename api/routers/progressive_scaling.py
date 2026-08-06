"""Progressive Scaling API — Endpoints for $3M → $10M scaling system.

Endpoints:
- GET /api/progressive-scaling/status — Current phase and metrics
- POST /api/progressive-scaling/update-metrics — Update monthly metrics
- POST /api/progressive-scaling/evaluate-progression — Check if can progress
- POST /api/progressive-scaling/progress — Force progression (if criteria met)
- GET /api/progressive-scaling/risk-status — Current risk levels
- POST /api/progressive-scaling/update-risk — Update risk values
- GET /api/progressive-scaling/triggers — Trigger system status
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.financial_intelligence.adaptive_success_rate import (
    OutcomeType,
    get_adaptive_success_rate_system,
)
from cores.financial_intelligence.auto_triggers import get_auto_trigger_system
from cores.financial_intelligence.progressive_scaling import (
    get_progressive_scaling_manager,
)
from cores.financial_intelligence.risk_monitor import (
    RiskType,
    get_risk_monitor,
)

router = APIRouter(prefix="/api/progressive-scaling", tags=["progressive-scaling"])
logger = logging.getLogger(__name__)


class MetricsUpdate(BaseModel):
    """Request model for updating metrics."""

    monthly_revenue: float = Field(..., description="Monthly revenue in USD")
    submissions: int = Field(..., description="Total submissions this month")
    accepted: int = Field(..., description="Accepted submissions this month")
    investment_return: float = Field(..., description="Monthly investment return in USD")
    current_capital: float = Field(..., description="Current total capital in USD")


class RiskUpdate(BaseModel):
    """Request model for updating risk values."""

    risk_type: str = Field(..., description="Type of risk (drawdown, leverage, position_size, etc.)")
    value: float = Field(..., description="Current risk value")


class AttemptRecord(BaseModel):
    """Request model for recording an attempt."""

    phase: str = Field(..., description="Phase of the attempt")
    attempt_type: str = Field(..., description="Type of attempt (bug_bounty, dev_bounty, investment, etc.)")
    target_value: float = Field(..., description="Target revenue or return")
    actual_value: float = Field(..., description="Actual revenue or return")
    outcome: str = Field(..., description="Outcome (success, failure, partial, pending)")
    predicted_probability: float = Field(..., description="Predicted success probability")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


@router.get("/status")
async def get_scaling_status() -> dict[str, Any]:
    """Get current scaling phase and metrics."""
    try:
        manager = get_progressive_scaling_manager()
        return manager.get_status()
    except Exception as e:
        logger.error(f"Failed to get scaling status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get scaling status: {str(e)}") from e


@router.post("/update-metrics")
async def update_metrics(request: MetricsUpdate) -> dict[str, Any]:
    """Update monthly metrics."""
    try:
        manager = get_progressive_scaling_manager()
        manager.update_metrics(
            monthly_revenue=request.monthly_revenue,
            submissions=request.submissions,
            accepted=request.accepted,
            investment_return=request.investment_return,
            current_capital=request.current_capital,
        )
        return {"status": "metrics_updated", "timestamp": datetime.now(UTC).isoformat()}
    except Exception as e:
        logger.error(f"Failed to update metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update metrics: {str(e)}") from e


@router.post("/evaluate-progression")
async def evaluate_progression() -> dict[str, Any]:
    """Evaluate if can progress to next phase."""
    try:
        manager = get_progressive_scaling_manager()
        decision = manager.evaluate_progression()
        return {
            "can_progress": decision.can_progress,
            "reason": decision.reason,
            "current_phase": decision.current_phase.value,
            "next_phase": decision.next_phase.value if decision.next_phase else None,
            "recommendation": decision.recommendation,
            "metrics": {
                "current_monthly_revenue": decision.metrics.current_monthly_revenue,
                "months_at_phase": decision.metrics.months_at_current_phase,
                "months_above_target": decision.metrics.months_above_target,
                "max_drawdown_pct": decision.metrics.max_drawdown_pct,
                "current_drawdown_pct": decision.metrics.current_drawdown_pct,
                "acceptance_rate": (
                    decision.metrics.accepted_submissions / decision.metrics.total_submissions
                    if decision.metrics.total_submissions > 0
                    else 0.0
                ),
            },
        }
    except Exception as e:
        logger.error(f"Failed to evaluate progression: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to evaluate progression: {str(e)}") from e


@router.post("/progress")
async def progress_to_next_phase() -> dict[str, Any]:
    """Progress to next phase if criteria are met."""
    try:
        manager = get_progressive_scaling_manager()
        success = manager.progress_to_next_phase()
        if success:
            return {
                "status": "progressed",
                "new_phase": manager.get_current_phase().value,
                "config": manager.get_current_config().__dict__,
            }
        else:
            decision = manager.evaluate_progression()
            return {
                "status": "not_eligible",
                "reason": decision.reason,
                "recommendation": decision.recommendation,
            }
    except Exception as e:
        logger.error(f"Failed to progress: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to progress: {str(e)}") from e


@router.get("/risk-status")
async def get_risk_status() -> dict[str, Any]:
    """Get current risk levels and alerts."""
    try:
        monitor = get_risk_monitor()
        return monitor.get_status()
    except Exception as e:
        logger.error(f"Failed to get risk status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get risk status: {str(e)}") from e


@router.post("/update-risk")
async def update_risk(request: RiskUpdate) -> dict[str, Any]:
    """Update risk value and check thresholds."""
    try:
        monitor = get_risk_monitor()
        risk_type = RiskType(request.risk_type)
        monitor.update_risk_value(risk_type, request.value)
        return {
            "status": "risk_updated",
            "risk_type": request.risk_type,
            "value": request.value,
            "current_level": monitor.get_current_level().value,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid risk type: {request.risk_type}") from e
    except Exception as e:
        logger.error(f"Failed to update risk: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update risk: {str(e)}") from e


@router.get("/triggers")
async def get_triggers_status() -> dict[str, Any]:
    """Get trigger system status."""
    try:
        trigger_system = get_auto_trigger_system()
        return trigger_system.get_status()
    except Exception as e:
        logger.error(f"Failed to get triggers status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get triggers status: {str(e)}") from e


@router.post("/check-triggers")
async def check_triggers() -> dict[str, Any]:
    """Check all triggers and execute if conditions met."""
    try:
        trigger_system = get_auto_trigger_system()
        results = trigger_system.check_triggers()
        return {
            "checked_at": datetime.now(UTC).isoformat(),
            "results": [
                {"type": trigger_type.value, "triggered": triggered}
                for trigger_type, triggered in results
            ],
        }
    except Exception as e:
        logger.error(f"Failed to check triggers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check triggers: {str(e)}") from e


@router.get("/config")
async def get_current_config() -> dict[str, Any]:
    """Get current phase configuration."""
    try:
        manager = get_progressive_scaling_manager()
        config = manager.get_current_config()
        return {
            "phase": manager.get_current_phase().value,
            "config": {
                "name": config.name,
                "target_annual": config.target_annual,
                "target_monthly": config.target_monthly,
                "multi_agent_concurrent": config.multi_agent_concurrent,
                "work_bank_jobs": config.work_bank_jobs,
                "acceptance_rate": config.acceptance_rate,
                "categories_count": config.categories_count,
                "freqtrade_leverage": config.freqtrade_leverage,
                "hummingbot_leverage": config.hummingbot_leverage,
                "polymarket_sizing": config.polymarket_sizing,
                "sports_betting_kelly": config.sports_betting_kelly,
                "stop_loss_pct": config.stop_loss_pct,
                "drawdown_limit_pct": config.drawdown_limit_pct,
                "required_stability_months": config.required_stability_months,
                "min_success_probability": config.min_success_probability,
                "risk_of_ruin": config.risk_of_ruin,
            },
        }
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}") from e


@router.get("/adaptive-probabilities")
async def get_adaptive_probabilities() -> dict[str, Any]:
    """Get current adaptive success probabilities (baseline vs learned)."""
    try:
        adaptive_system = get_adaptive_success_rate_system()
        return adaptive_system.get_current_probabilities()
    except Exception as e:
        logger.error(f"Failed to get adaptive probabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get adaptive probabilities: {str(e)}") from e


@router.post("/record-attempt")
async def record_attempt(request: AttemptRecord) -> dict[str, Any]:
    """Record an attempt with outcome and update learned probabilities."""
    try:
        adaptive_system = get_adaptive_success_rate_system()
        attempt_id = adaptive_system.record_attempt(
            phase=request.phase,
            attempt_type=request.attempt_type,
            target_value=request.target_value,
            actual_value=request.actual_value,
            outcome=OutcomeType(request.outcome),
            predicted_probability=request.predicted_probability,
            metadata=request.metadata,
        )
        return {
            "status": "attempt_recorded",
            "attempt_id": attempt_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid outcome type: {request.outcome}") from e
    except Exception as e:
        logger.error(f"Failed to record attempt: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record attempt: {str(e)}") from e


@router.get("/trajectory")
async def get_improvement_trajectory() -> dict[str, Any]:
    """Get improvement trajectory of success rates over time."""
    try:
        adaptive_system = get_adaptive_success_rate_system()
        return adaptive_system.get_improvement_trajectory()
    except Exception as e:
        logger.error(f"Failed to get trajectory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get trajectory: {str(e)}") from e


@router.get("/statistics")
async def get_adaptive_statistics() -> dict[str, Any]:
    """Get comprehensive statistics from adaptive learning system."""
    try:
        adaptive_system = get_adaptive_success_rate_system()
        return adaptive_system.get_statistics()
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}") from e
