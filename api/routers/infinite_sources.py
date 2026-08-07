"""Infinite Sources API — Endpoints for continuous zero-barrier source discovery.

Endpoints:
- GET /api/infinite-sources/status — Current discovery status
- POST /api/infinite-sources/discover — Trigger discovery scan
- GET /api/infinite-sources/opportunities — Get discovered opportunities
- GET /api/infinite-sources/criteria — Get current criteria
- POST /api/infinite-sources/update-criteria — Update zero-barrier criteria
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.financial_intelligence.infinite_source_discovery import (
    get_infinite_source_discovery,
)

router = APIRouter(prefix="/api/infinite-sources", tags=["infinite-sources"])
logger = logging.getLogger(__name__)


class CriteriaUpdate(BaseModel):
    """Request model for updating zero-barrier criteria."""

    no_experience_required: bool | None = None
    max_experience_months: int | None = None
    no_interview_required: bool | None = None
    min_hourly_rate: float | None = None
    instant_start: bool | None = None


@router.get("/status")
async def get_discovery_status() -> dict[str, Any]:
    """Get current infinite source discovery status."""
    try:
        discovery = get_infinite_source_discovery()
        return discovery.get_status()
    except Exception as e:
        logger.error(f"Failed to get discovery status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get discovery status: {str(e)}") from e


@router.post("/discover")
async def discover_sources(limit: int = 50) -> dict[str, Any]:
    """Trigger infinite source discovery scan."""
    try:
        discovery = get_infinite_source_discovery()
        opportunities = discovery.discover_sources(limit=limit)
        return {
            "status": "discovery_complete",
            "discovered_count": len(opportunities),
            "opportunities": [opp.to_dict() for opp in opportunities],
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to discover sources: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to discover sources: {str(e)}") from e


@router.get("/opportunities")
async def get_discovered_opportunities() -> dict[str, Any]:
    """Get all discovered opportunities."""
    try:
        discovery = get_infinite_source_discovery()
        return {
            "total_discovered": len(discovery._discovered_opportunities),
            "opportunities": [opp.to_dict() for opp in discovery._discovered_opportunities],
        }
    except Exception as e:
        logger.error(f"Failed to get opportunities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get opportunities: {str(e)}") from e


@router.get("/criteria")
async def get_criteria() -> dict[str, Any]:
    """Get current zero-barrier criteria."""
    try:
        discovery = get_infinite_source_discovery()
        return {
            "no_experience_required": discovery.criteria.no_experience_required,
            "max_experience_months": discovery.criteria.max_experience_months,
            "no_interview_required": discovery.criteria.no_interview_required,
            "no_portfolio_required": discovery.criteria.no_portfolio_required,
            "instant_start": discovery.criteria.instant_start,
            "min_hourly_rate": discovery.criteria.min_hourly_rate,
            "pay_frequency": discovery.criteria.pay_frequency,
        }
    except Exception as e:
        logger.error(f"Failed to get criteria: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get criteria: {str(e)}") from e


@router.post("/update-criteria")
async def update_criteria(request: CriteriaUpdate) -> dict[str, Any]:
    """Update zero-barrier criteria."""
    try:
        discovery = get_infinite_source_discovery()

        # Update only provided fields
        if request.no_experience_required is not None:
            discovery.criteria.no_experience_required = request.no_experience_required
        if request.max_experience_months is not None:
            discovery.criteria.max_experience_months = request.max_experience_months
        if request.no_interview_required is not None:
            discovery.criteria.no_interview_required = request.no_interview_required
        if request.min_hourly_rate is not None:
            discovery.criteria.min_hourly_rate = request.min_hourly_rate
        if request.instant_start is not None:
            discovery.criteria.instant_start = request.instant_start

        return {
            "status": "criteria_updated",
            "updated_criteria": {
                "no_experience_required": discovery.criteria.no_experience_required,
                "max_experience_months": discovery.criteria.max_experience_months,
                "no_interview_required": discovery.criteria.no_interview_required,
                "instant_start": discovery.criteria.instant_start,
                "min_hourly_rate": discovery.criteria.min_hourly_rate,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to update criteria: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update criteria: {str(e)}") from e
