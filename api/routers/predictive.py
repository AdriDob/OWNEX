"""Predictive Target Prioritization API Router — 7-day empirical forecast."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body

from cores.learning.predictive_prioritizer import (
    DEFAULT_DAILY_HOURS,
    get_predictive_prioritizer,
)

logger = logging.getLogger("ownex.api.predictive")

router = APIRouter(prefix="/api/predictive", tags=["predictive-prioritization"])


@router.post("/forecast")
async def forecast(
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Rank candidate targets for the next 7 days by predicted EV/hour.

    Body: {"candidates": [{id, name, platform?, program?, reward?, hours?,
    last_finding_days_ago?}], "daily_hours": 4.0}
    """
    candidates = payload.get("candidates") or []
    daily_hours = float(payload.get("daily_hours", DEFAULT_DAILY_HOURS))
    return get_predictive_prioritizer().forecast(candidates, daily_hours=daily_hours)


@router.get("/latest")
async def latest() -> dict[str, Any] | None:
    """Get the latest persisted forecast."""
    return get_predictive_prioritizer().latest_forecast()


@router.get("/methods")
async def methods() -> dict[str, Any]:
    """Introspect forecasting internals (honest): outcomes source + model defaults."""
    with __import__("contextlib").suppress(Exception):
        from cores.learning.predictive_prioritizer import (
            MAX_ACCEPTANCE,
            MIN_ACCEPTANCE,
            MIN_SAMPLES_FOR_CONFIDENCE,
            RECENCY_WINDOW_DAYS,
        )

        model = {
            "method": "empirical_bayes_clamp",
            "acceptance_clamp": [MIN_ACCEPTANCE, MAX_ACCEPTANCE],
            "min_samples_for_confidence": MIN_SAMPLES_FOR_CONFIDENCE,
            "recency_window_days": RECENCY_WINDOW_DAYS,
            "ndep": 0,  # zero external ML dependencies
        }
    return model
