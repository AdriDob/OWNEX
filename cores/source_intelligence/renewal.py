"""Source Renewal Agent — Automatic health checks, renewal decisions, and source retirement.

This module implements the automatic renewal cycle for sources:
- Runs health checks on all sources on a schedule
- Determines which sources to renew (re-verify) vs retire
- Updates source status in the registry
- Generates renewal reports
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .registry import SourceStatus


class RenewalDecision(Enum):
    """Decision for a source renewal cycle."""

    RENEW = "renew"  # Re-run verification, likely still valid
    REFRESH = "refresh"  # Re-verify, may need updates
    RETIRE = "retire"  # Source no longer valuable, remove
    MONITOR = "monitor"  # Keep watching, re-verify soon


@dataclass
class RenewalSchedule:
    """Schedule for running renewal checks."""

    interval_hours: int = 24  # Check every 24 hours by default
    critical_interval_hours: int = 4  # Critical sources checked every 4 hours
    stale_threshold_days: int = 7  # Mark stale after 7 days without verification
    retire_threshold_days: int = 30  # Retire source not verified in 30 days


@dataclass
class RenewalResult:
    """Result of a single source renewal cycle."""

    source_id: str
    source_name: str
    decision: RenewalDecision
    reason: str
    new_verification: Any | None = None  # New VerificationCheck if renewed
    should_remove: bool = False  # Whether to remove from registry
    update_status: bool = False  # Whether to update source status


class RenewalAgent:
    """Automatic source renewal agent.

    Runs on a schedule and decides for each source whether to:
    - Renew (re-verify, likely still valid)
    - Refresh (re-verify, may need updates)
    - Retire (no longer valuable)
    - Monitor (keep watching, re-verify soon)
    """

    def __init__(self, registry, verifier, intelligence, schedule: RenewalSchedule | None = None):
        self.registry = registry
        self.verifier = verifier
        self.intelligence = intelligence
        self.schedule = schedule or RenewalSchedule()
        self.cycle_count = 0

    def run_renewal_cycle(self) -> list[RenewalResult]:
        """Run one complete renewal cycle across all sources.

        Returns:
            List of RenewalResult, one per source
        """
        self.cycle_count += 1
        results = []

        sources = self.registry.all_sources()

        for source in sources:
            result = self._renew_source(source)
            results.append(result)

        return results

    def _renew_source(self, source: SourceInfo) -> RenewalResult:
        """Run renewal for a single source."""
        source_id = source.source_id
        source_name = source.name

        # Check when last was verified
        last_verified = source.last_verified
        now = datetime.now()

        if last_verified is None:
            # Never verified - need full verification
            decision = RenewalDecision.RENEW
            reason = "Never verified - run full verification pipeline"

            # Run verification
            try:
                verdict = self.verifier.verify_source(source_id, source_name)
                new_verification = verdict  # The full verdict has all checks
            except Exception as e:
                decision = RenewalDecision.RETIRE
                reason = f"Error during verification: {str(e)[:100]}"
                new_verification = None
        elif (now - datetime.fromisoformat(last_verified)).days >= self.schedule.retire_threshold_days:
            # Not verified in 30+ days - retire
            decision = RenewalDecision.RETIRE
            reason = f"Not verified in {self.schedule.retire_threshold_days}+ days - retiring"
            new_verification = None
        elif (now - datetime.fromisoformat(last_verified)).days >= self.schedule.stale_threshold_days:
            # Stale (7+ days) - refresh/renew
            decision = RenewalDecision.RENEW
            reason = "Stale verification (>7 days) - renewing verification"

            # Run renewal verification
            try:
                verdict = self.verifier.verify_source(source_id, source_name)
                new_verification = verdict
            except Exception as e:
                decision = RenewalDecision.RETIRE
                reason = f"Error renewing verification: {str(e)[:100]}"
                new_verification = None
        else:
            # Recently verified - just monitor, maybe refresh
            # Check if source status suggests monitoring
            if source.status in [SourceStatus.DEGRADED, SourceStatus.UNKNOWN]:
                decision = RenewalDecision.RENEW
                reason = "Source status degraded or unknown - renew verification"

                try:
                    verdict = self.verifier.verify_source(source_id, source_name)
                    new_verification = verdict
                except Exception as e:
                    decision = RenewalDecision.MONITOR
                    reason = f"Error during renewal: {str(e)[:100]}"
                    new_verification = None
            else:
                # Good standing - just monitor
                decision = RenewalDecision.MONITOR
                reason = "Source recently verified and in good standing - monitoring"
                new_verification = None

        # Determine should_remove and update_status
        should_remove = decision == RenewalDecision.RETIRE
        update_status = decision in [RenewalDecision.RENEW, RenewalDecision.RETIRE]

        return RenewalResult(
            source_id=source_id,
            source_name=source_name,
            decision=decision,
            reason=reason,
            new_verification=new_verification,
            should_remove=should_remove,
            update_status=update_status,
        )

    def decide_renewal(self, source_id: str) -> RenewalDecision:
        """Get renewal decision for a specific source without running full cycle."""
        source = self.registry.get(source_id)
        if source is None:
            return RenewalDecision.RETIRE
        return self._renew_source(source).decision

    def get_priority_renewal_list(self, max_sources: int = 10) -> list[tuple[str, RenewalDecision]]:
        """Get list of sources needing renewal, prioritized.

        Returns list of (source_id, decision) sorted by priority.
        Critical sources are checked first.
        """
        results = []
        sources = self.registry.all_sources()

        # Sort by criticality: CRITICAL > HIGH > MEDIUM > LOW > RETIRE
        status_order = {
            SourceStatus.ACTIVE: 0,
            SourceStatus.DEGRADED: 1,
            SourceStatus.UNKNOWN: 2,
            SourceStatus.INACTIVE: 3,
            SourceStatus.RETIRED: 4,
        }

        sources.sort(key=lambda s: status_order.get(s.status, 99))

        for source in sources[: max_sources * 2]:  # Check a few extra
            decision = self.decide_renewal(source.source_id)
            results.append((source.source_id, decision))

        return results[:max_sources]
