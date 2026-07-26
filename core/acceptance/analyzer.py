"""Acceptance Intelligence — historical pattern analysis.

Analyzes past submission outcomes to discover which report
characteristics correlate with acceptance on each platform.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from core.acceptance.models import AcceptanceOutcome, PlatformProfile

logger = logging.getLogger("orion.core.acceptance.analyzer")


class AcceptanceAnalyzer:
    """Analyzes historical submission outcomes to extract acceptance patterns."""

    def __init__(self) -> None:
        self._outcomes: list[AcceptanceOutcome] = []
        self._profiles: dict[str, PlatformProfile] = {}

    def record_outcome(self, outcome: AcceptanceOutcome) -> None:
        """Record a single submission outcome and update profiles."""
        self._outcomes.append(outcome)

        platform = outcome.platform.lower()
        if platform not in self._profiles:
            self._profiles[platform] = PlatformProfile(platform=platform)
        self._profiles[platform].update(outcome)

    def record_batch(self, outcomes: list[AcceptanceOutcome]) -> None:
        """Record multiple outcomes at once."""
        for o in outcomes:
            self.record_outcome(o)

    def get_profile(self, platform: str) -> PlatformProfile | None:
        """Get the learned profile for a platform."""
        return self._profiles.get(platform.lower())

    def all_profiles(self) -> dict[str, PlatformProfile]:
        """Get all platform profiles."""
        return dict(self._profiles)

    def top_vulnerability_types(self, platform: str, min_samples: int = 3) -> list[dict[str, Any]]:
        """Return vulnerability types sorted by acceptance rate."""
        profile = self._profiles.get(platform.lower())
        if not profile:
            return []

        sorted_types = sorted(
            profile.by_type.items(),
            key=lambda x: x[1]["rate"],
            reverse=True,
        )
        return [{"type": vt, **stats} for vt, stats in sorted_types if stats["total"] >= min_samples]

    def worst_vulnerability_types(self, platform: str, min_samples: int = 3) -> list[dict[str, Any]]:
        """Return vulnerability types sorted by rejection rate (ascending acceptance)."""
        profile = self._profiles.get(platform.lower())
        if not profile:
            return []

        sorted_types = sorted(
            profile.by_type.items(),
            key=lambda x: x[1]["rate"],
        )
        return [{"type": vt, **stats} for vt, stats in sorted_types if stats["total"] >= min_samples]

    def best_severity_for_type(self, platform: str, vuln_type: str) -> str | None:
        """Find the severity level with highest acceptance for a given vuln type."""
        profile = self._profiles.get(platform.lower())
        if not profile:
            return None

        relevant = [(sev, stats) for sev, stats in profile.by_severity.items() if stats["total"] > 0]
        if not relevant:
            return None
        best = max(relevant, key=lambda x: x[1]["rate"])
        return best[0]

    def acceptance_trend(self, platform: str) -> dict[str, Any]:
        """Return acceptance rate trend over time (by month)."""
        platform_outcomes = [o for o in self._outcomes if o.platform.lower() == platform.lower() and o.submitted_at]
        if not platform_outcomes:
            return {"months": 0, "trend": "stable", "recent_rate": 0.0, "overall_rate": 0.0}

        sorted_outcomes = sorted(platform_outcomes, key=lambda o: o.submitted_at or "")
        total = len(sorted_outcomes)
        accepted = sum(1 for o in sorted_outcomes if o.status in ("accepted", "won"))
        recent = sorted_outcomes[-max(total // 3, 1) :]
        recent_accepted = sum(1 for o in recent if o.status in ("accepted", "won"))

        overall_rate = accepted / max(total, 1)
        recent_rate = recent_accepted / max(len(recent), 1)

        if recent_rate > overall_rate * 1.1:
            trend = "improving"
        elif recent_rate < overall_rate * 0.9:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "total": total,
            "accepted": accepted,
            "overall_rate": round(overall_rate, 3),
            "recent_count": len(recent),
            "recent_accepted": recent_accepted,
            "recent_rate": round(recent_rate, 3),
            "trend": trend,
        }

    def summary(self) -> dict[str, Any]:
        """Return a comprehensive summary of all acceptance data."""
        total_outcomes = len(self._outcomes)
        total_platforms = len(self._profiles)
        accepted = sum(1 for o in self._outcomes if o.status in ("accepted", "won"))
        rejected = sum(1 for o in self._outcomes if o.status in ("rejected", "dismissed"))
        pending = sum(1 for o in self._outcomes if o.status == "pending")
        total_payout = sum(o.payout for o in self._outcomes if o.status in ("accepted", "won"))

        by_type: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "accepted": 0})
        for o in self._outcomes:
            by_type[o.vulnerability_type]["total"] += 1
            if o.status in ("accepted", "won"):
                by_type[o.vulnerability_type]["accepted"] += 1

        by_platform: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "accepted": 0})
        for o in self._outcomes:
            by_platform[o.platform.lower()]["total"] += 1
            if o.status in ("accepted", "won"):
                by_platform[o.platform.lower()]["accepted"] += 1

        return {
            "total_outcomes": total_outcomes,
            "total_platforms": total_platforms,
            "accepted": accepted,
            "rejected": rejected,
            "pending": pending,
            "acceptance_rate": round(accepted / max(total_outcomes, 1), 3),
            "total_payout": round(total_payout, 2),
            "avg_payout": round(total_payout / max(accepted, 1), 2),
            "by_type": dict(by_type),
            "by_platform": dict(by_platform),
            "profiles": {p: pf.to_dict() for p, pf in self._profiles.items()},
        }
