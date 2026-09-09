from __future__ import annotations

import logging
from typing import Any

from core.opportunity.models import PersonalHistory
from core.revenue.metrics import RevenueMetrics

logger = logging.getLogger("ownex.opportunity.personal")


class PersonalHistoryTracker:
    def __init__(self, metrics: RevenueMetrics | None = None) -> None:
        self._metrics = metrics or RevenueMetrics()

    def get_history(self) -> PersonalHistory:
        acceptance = self._metrics.acceptance_rate()
        total_submissions = sum(d.get("total", 0) for d in acceptance.values())
        total_accepted = sum(d.get("accepted", 0) for d in acceptance.values())
        resolved = total_submissions - sum(d.get("pending", 0) for d in acceptance.values())
        personal_rate = total_accepted / max(resolved, 1)

        payout_summary = self._metrics.payout_summary()
        total_payout = payout_summary.get("total_payout", 0.0)
        total_count = payout_summary.get("total_count", 0)
        avg_payout = total_payout / max(total_count, 1)

        time_data = self._metrics.time_metrics()
        avg_days = time_data.get("avg_days_to_acceptance", 0.0)

        by_platform: dict[str, dict[str, Any]] = {}
        for platform, data in acceptance.items():
            p_resolved = data.get("accepted", 0) + data.get("rejected", 0)
            p_rate = data.get("accepted", 0) / max(p_resolved, 1)
            by_platform[platform] = {
                "acceptance_rate": p_rate,
                "total": data.get("total", 0),
                "accepted": data.get("accepted", 0),
            }

        by_vuln_type: dict[str, dict[str, Any]] = {}
        for entry in self._metrics.roi_by_vuln_type():
            vt = entry.get("vuln_type", "unknown")
            by_vuln_type[vt] = {
                "total_payout": entry.get("total_payout", 0.0),
                "count": entry.get("count", 0),
                "avg_payout": entry.get("avg_payout", 0.0),
            }

        competition_level = max(0.0, min(1.0, 1.0 - personal_rate))

        return PersonalHistory(
            personal_acceptance_rate=round(personal_rate, 3),
            personal_avg_payout=round(avg_payout, 2),
            personal_avg_days=round(avg_days, 1),
            personal_competition_level=round(competition_level, 3),
            total_submissions=total_submissions,
            total_accepted=total_accepted,
            by_platform=by_platform,
            by_vuln_type=by_vuln_type,
        )
