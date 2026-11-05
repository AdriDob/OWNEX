"""OWNEX Earnings Tracker — Crypto AI Platforms Integration.

Tracks income from 7 crypto/AI platforms for Argentina-based operation:
- Sahara AI, Outlier AI, Gitcoin, Immunefi, PublicAI, Sapien,
  CODEFORAI.tech, DATAANNOTATION.tech

All platforms pay in USDC/USDT crypto, no human interviews,
payout via Airtm to Argentine pesos.

Example usage:
    from core.earnings import tracker
    tracker.report_task("outlier_ai", earnings_usd=5.50, task_success=True)
    tracker.show_status()
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from database.db import SessionLocal
from database.models_economic import AdapterPerformanceMetrics

logger = logging.getLogger("core.earnings")

# 7 platforms tracked
PLATFORMS = [
    "sahara_ai",
    "outlier_ai",
    "gitcoin",
    "immunefi",
    "publicai",
    "codeforai",
    "dataannotation",
]

DEFAULT_CONFIG = {
    "airtm_handle": "",
    "meta_mask_address": "",
    "kyc_verified": False,
    "first_retiro_testado": False,
    "retiro_total_usd": 0.0,
    "retiros_count": 0,
}


class EarningsTracker:
    """Tracker for crypto AI platform earnings with adapter priority integration."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session or SessionLocal()
        # Initialize adapter metrics if table exists
        try:
            self._ensure_adapter_table()
        except Exception as e:
            logger.warning(f"Could not ensure adapter table: {e}")

    def _ensure_adapter_table(self) -> None:
        """Ensure adapter_performance_metrics table exists."""
        with contextlib.suppress(Exception):
            # Table should already exist from migration/Create
            # Just verify it's accessible
            self.session.query(AdapterPerformanceMetrics).limit(1).all()

    def report_task(
        self,
        platform: str,
        adapter_name: str | None = None,
        earnings_usd: float = 0.0,
        success: bool = True,
        response_time_ms: int | None = None,
    ) -> dict[str, Any]:
        """Report a completed task on a platform.

        Updates both the platform earnings AND the adapter performance metrics.

        Args:
            platform: One of PLATFORMS list
            adapter_name: Name of adapter (if applicable)
            earnings_usd: Earnings in USD from this task
            success: Whether the task succeeded
            response_time_ms: Time taken in ms (for adapter tracking)

        Returns:
            dict with updated earnings state
        """
        if platform not in PLATFORMS:
            logger.warning(f"Unknown platform: {platform}")
            return {"error": f"Platform {platform} not in known list"}

        # Update adapter performance metrics if adapter_name provided
        if adapter_name:
            self._update_adapter_metrics(adapter_name, success, response_time_ms)

        # Update platform earnings (simplified - in production would have
        # per-platform detailed tracking)
        result = {
            "platform": platform,
            "earnings_usd": round(self.session._last_earnings + earnings_usd, 2) if hasattr(self.session, "_last_earnings") else round(earnings_usd, 2),
            "success": success,
            "adapter_name": adapter_name,
        }

        logger.info(f"Task reported: {platform} +${earnings_usd} (success={success})")
        return result

    def _update_adapter_metrics(self, adapter_name: str, success: bool, response_time_ms: int | None) -> None:
        """Update adapter_performance_metrics for given adapter."""
        try:
            metric = self.session.query(AdapterPerformanceMetrics).filter(AdapterPerformanceMetrics.adapter_name == adapter_name).first()

            if metric is None:
                # Create new adapter metric entry
                metric = AdapterPerformanceMetrics(
                    adapter_name=adapter_name,
                    category=self._determine_category(adapter_name),
                    last_activity=datetime.now(UTC),
                    success_count=1 if success else 0,
                    failure_count=0 if success else 1,
                    total_requests=1,
                    avg_response_time_ms=response_time_ms or 0,
                    is_active=True,
                    last_validated=datetime.now(UTC),
                    meta_json=json.dumps({}),
                )
                self.session.add(metric)
            else:
                # Update existing
                metric.success_count = (metric.success_count or 0) + (1 if success else 0)
                metric.failure_count = (metric.failure_count or 0) + (0 if success else 1)
                metric.total_requests = (metric.total_requests or 0) + 1
                if response_time_ms is not None:
                    metric.avg_response_time_ms = round(
                        ((metric.avg_response_time_ms or 0) * (metric.total_requests - 1) + response_time_ms) / metric.total_requests
                        if metric.total_requests > 0
                        else response_time_ms
                    )
                metric.last_activity = datetime.now(UTC)
                metric.last_validated = datetime.now(UTC)

            metric.updated_at = datetime.now(UTC)
            self.session.commit()

        except Exception as e:
            logger.error(f"Error updating adapter metrics for {adapter_name}: {e}")
            self.session.rollback()

    @staticmethod
    def _determine_category(adapter_name: str) -> str:
        """Determine adapter category from name."""
        name_lower = adapter_name.lower()
        if any(kw in name_lower for kw in ["hackerone", "bugcrowd", "intigriti", "imunefi"]):
            return "bounty"
        elif any(kw in name_lower for kw in ["ccxt", "trading", "future", "defi", "forex", "crypto", "stocks"]):
            return "trading"
        elif any(kw in name_lower for kw in ["sahara", "outlier", "dataannotation"]):
            return "ai_training"
        elif any(kw in name_lower for kw in ["sensor", "monitor", "ping"]):
            return "sensor"
        else:
            return "other"

    def show_status(self) -> dict[str, Any]:
        """Show complete earnings and adapter status dashboard.

        Returns:
            dict with summary of all earnings and adapter priorities
        """
        try:
            # Get adapter metrics sorted by priority
            adapters = self.session.query(AdapterPerformanceMetrics).order_by(AdapterPerformanceMetrics.priority_score.desc()).all()

            # Summary by category
            from collections import defaultdict

            cat_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "total_score": 0.0, "adapters": []})

            for a in adapters:
                cat = a.category
                cat_stats[cat]["count"] += 1
                cat_stats[cat]["total_score"] += a.priority_score_calculated
                cat_stats[cat]["adapters"].append(
                    {
                        "name": a.adapter_name,
                        "score": a.priority_score_calculated,
                        "active": a.is_active,
                    }
                )

            # Calculate totals
            total_adapters = sum(c["count"] for c in cat_stats.values())
            total_score = sum(c["total_score"] for c in cat_stats.values())

            # Top 10 prioritized adapters
            top_adapters = [
                {
                    "rank": i + 1,
                    "name": a.adapter_name,
                    "score": a.priority_score_calculated,
                    "category": a.category,
                    "active": a.is_active,
                    "total_requests": a.total_requests,
                    "success_rate": a.success_rate,
                    "recency": a.recency_score,
                }
                for i, a in enumerate(adapters[:10])
            ]

            return {
                "total_adapters": total_adapters,
                "total_priority_score": round(total_score, 4),
                "by_category": {
                    cat: {
                        "count": stats["count"],
                        "avg_score": round(stats["total_score"] / stats["count"], 4) if stats["count"] > 0 else 0,
                        "top": sorted(stats["adapters"], key=lambda x: x["score"], reverse=True)[:3],
                    }
                    for cat, stats in cat_stats.items()
                },
                "top_10_adapters": top_adapters,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error showing earnings status: {e}")
            return {"error": str(e)}

    def get_top_adapters(self, n: int = 10) -> list[dict[str, Any]]:
        """Get top N adapters by priority score.

        Returns list of dicts with adapter performance info.
        """
        adapters = self.session.query(AdapterPerformanceMetrics).order_by(AdapterPerformanceMetrics.priority_score.desc()).limit(n).all()

        return [
            {
                "rank": i + 1,
                "name": a.adapter_name,
                "priority_score": a.priority_score_calculated,
                "category": a.category,
                "is_active": a.is_active,
                "total_requests": a.total_requests,
                "success_rate": a.success_rate,
                "recency_score": a.recency_score,
                "last_activity": a.last_activity.isoformat() if a.last_activity else None,
            }
            for i, a in enumerate(adapters)
        ]


# Global tracker instance for convenience
_tracker_instance: EarningsTracker | None = None


def get_tracker() -> EarningsTracker:
    """Get or create the global earnings tracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = EarningsTracker()
    return _tracker_instance


def report_task(
    platform: str,
    adapter_name: str | None = None,
    earnings_usd: float = 0.0,
    success: bool = True,
    response_time_ms: int | None = None,
) -> dict[str, Any]:
    """Convenience function to report a task."""
    return get_tracker().report_task(platform, adapter_name, earnings_usd, success, response_time_ms)


def show_status() -> dict[str, Any]:
    """Convenience function to show status."""
    return get_tracker().show_status()


def get_top_adapters(n: int = 10) -> list[dict[str, Any]]:
    """Convenience function to get top adapters."""
    return get_tracker().get_top_adapters(n)
