"""Dev Bounty Automation — Connects WorkBank → CoderAgent → AutoSubmit.

When WorkBank finds a dev bounty opportunity (Algora, Opire, IssueHunt, etc.),
this module orchestrates:
1. CoderAgent solves the issue (clone → analyze → fix → test → PR)
2. AutoSubmitEngine submits the PR to the platform
3. WorkBank marks as delivered and folds outcome to profile
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.autonomy.coder_agent import CoderAgent, CoderAgentConfig, CoderAgentResult, solve_issue
from core.opportunity.executors.auto_submit import SubmissionStatus, get_auto_submit_engine
from core.opportunity.models import Opportunity

logger = logging.getLogger("ownex.dev_bounty_automation")


# Platforms that support CoderAgent automation
CODER_AGENT_PLATFORMS = {
    "algora",
    "opire",
    "issuehunt",
    "github",
    "freelancer",
}


@dataclass
class DevBountyAutomationResult:
    """Result of automating a dev bounty opportunity."""

    opportunity_id: str
    platform: str
    success: bool
    coder_result: CoderAgentResult | None = None
    submission_status: SubmissionStatus | None = None
    pr_url: str | None = None
    error: str | None = None
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "platform": self.platform,
            "success": self.success,
            "coder_success": self.coder_result.success if self.coder_result else False,
            "submission_status": self.submission_status.value if self.submission_status else None,
            "pr_url": self.pr_url,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
        }


class DevBountyAutomationEngine:
    """Orchestrates end-to-end dev bounty automation."""

    def __init__(self, coder_config: CoderAgentConfig | None = None):
        self.coder_agent = CoderAgent(coder_config)
        self.auto_submit = get_auto_submit_engine()
        self._running: set[str] = set()  # Track running automations

    async def automate_opportunity(
        self,
        opportunity: Opportunity,
        force: bool = False,
    ) -> DevBountyAutomationResult:
        """Automate a single dev bounty opportunity end-to-end.

        Flow:
        1. Check if platform supports automation
        2. Run CoderAgent to solve issue and create PR
        3. Submit PR via AutoSubmitEngine
        4. Return consolidated result
        """
        start_time = datetime.now(UTC)
        opportunity_id = opportunity.id
        platform = opportunity.platform.value if hasattr(opportunity.platform, "value") else str(opportunity.platform)

        if opportunity_id in self._running:
            return DevBountyAutomationResult(
                opportunity_id=opportunity_id,
                platform=platform,
                success=False,
                error="Already running",
            )

        self._running.add(opportunity_id)
        logger.info(f"Starting dev bounty automation for {opportunity_id} on {platform}")

        try:
            # Step 1: Run CoderAgent to solve issue and create PR
            logger.info(f"Running CoderAgent for {opportunity_id}")
            coder_result = await self._run_coder_agent(opportunity)

            if not coder_result.success:
                return DevBountyAutomationResult(
                    opportunity_id=opportunity_id,
                    platform=platform,
                    success=False,
                    coder_result=coder_result,
                    error=f"CoderAgent failed: {coder_result.error}",
                    started_at=start_time.isoformat(),
                    completed_at=datetime.now(UTC).isoformat(),
                    duration_seconds=(datetime.now(UTC) - start_time).total_seconds(),
                )

            pr_url = coder_result.pr_result.pr_url if coder_result.pr_result else None
            logger.info(f"CoderAgent created PR: {pr_url}")

            # Step 2: Submit via AutoSubmitEngine
            # Build opportunity dict for submission
            submission_opportunity = {
                "id": opportunity_id,
                "title": opportunity.title,
                "platform": platform,
                "category": opportunity.category.value
                if hasattr(opportunity.category, "value")
                else str(opportunity.category),
                "reward": opportunity.payment,
                "description": opportunity.description,
                "url": pr_url,  # PR URL is the submission target
            }

            submission_record = await self.auto_submit.submit_workbank_item(
                item_id=opportunity_id,
                platform=platform,
                opportunity=submission_opportunity,
                force=False,
            )

            completed_at = datetime.now(UTC).isoformat()
            duration = (datetime.now(UTC) - start_time).total_seconds()

            return DevBountyAutomationResult(
                opportunity_id=opportunity_id,
                platform=platform,
                success=submission_record.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.CONFIRMED),
                coder_result=coder_result,
                submission_status=submission_record.status,
                pr_url=pr_url,
                error=submission_record.last_error if submission_record.status == SubmissionStatus.DLQ else None,
                started_at=start_time.isoformat(),
                completed_at=completed_at,
                duration_seconds=duration,
            )

        except Exception as exc:
            logger.exception(f"Dev bounty automation failed for {opportunity_id}: {exc}")
            completed_at = datetime.now(UTC).isoformat()
            duration = (datetime.now(UTC) - start_time).total_seconds()
            return DevBountyAutomationResult(
                opportunity_id=opportunity_id,
                platform=platform,
                success=False,
                error=str(exc),
                started_at=start_time.isoformat(),
                completed_at=completed_at,
                duration_seconds=duration,
            )
        finally:
            self._running.discard(opportunity_id)

    async def _run_coder_agent(self, opportunity: Opportunity) -> CoderAgentResult:
        """Run CoderAgent on the opportunity."""
        platform = opportunity.platform.value if hasattr(opportunity.platform, "value") else str(opportunity.platform)

        # Build issue data from opportunity
        issue_data = {
            "id": opportunity.id,
            "title": opportunity.title,
            "body": opportunity.description or "",
            "url": opportunity.url or "",
            "platform": platform,
            "repository": {
                "html_url": opportunity.metadata.get("repository_url", "") if hasattr(opportunity, "metadata") else "",
            },
        }

        # Use the convenience function
        return await solve_issue(
            issue_data=issue_data,
            repo_url=opportunity.metadata.get("repository_url", "") if hasattr(opportunity, "metadata") else "",
            platform=platform,
        )

    async def automate_batch(
        self,
        opportunities: list[Opportunity],
        max_concurrent: int = 2,
    ) -> list[DevBountyAutomationResult]:
        """Automate multiple opportunities with concurrency control."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_one(opp: Opportunity) -> DevBountyAutomationResult:
            async with semaphore:
                return await self.automate_opportunity(opp)

        tasks = [run_one(opp) for opp in opportunities]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            r
            if isinstance(r, DevBountyAutomationResult)
            else DevBountyAutomationResult(
                opportunity_id="unknown",
                platform="unknown",
                success=False,
                error=str(e),
            )
            for r, e in zip(results, [None] * len(results))
        ]

    def is_running(self, opportunity_id: str) -> bool:
        return opportunity_id in self._running


# Convenience function
async def automate_dev_bounty(
    opportunity: Opportunity,
    coder_config: CoderAgentConfig | None = None,
) -> DevBountyAutomationResult:
    """Simple function to automate a single dev bounty."""
    engine = DevBountyAutomationEngine(coder_config)
    return await engine.automate_opportunity(opportunity)


# Scheduler integration
async def run_dev_bounty_automation_cycle(
    target: int | None = None,
    profile: Any | None = None,
) -> dict[str, Any]:
    """Scheduler entry point: run dev bounty automation for ready opportunities.

    Finds ready-to-deliver dev bounty items in WorkBank and attempts automation.
    """
    from cores.direct_work_engine.engine import DirectWorkEngine
    from cores.direct_work_engine.models import OpportunityCategory

    engine = DirectWorkEngine()

    # Register adapters for dev bounty platforms
    try:
        from api.adapters.legacy import build_default_adapters

        for adapter in build_default_adapters():
            if adapter.source.platform not in engine.discovery.adapters:
                engine.register_adapter(adapter)
    except Exception as exc:
        logger.warning(f"Could not register adapters: {exc}")

    # Discover opportunities
    opportunities = await engine.discovery.discover_all() or []

    # Filter for dev bounty categories that support automation
    dev_bounty_categories = {
        OpportunityCategory.DEV_BOUNTY,
        OpportunityCategory.SOFTWARE_ENGINEERING,
        OpportunityCategory.BACKEND,
        OpportunityCategory.FRONTEND,
        OpportunityCategory.FULL_STACK,
        OpportunityCategory.API_DEVELOPMENT,
        OpportunityCategory.MOBILE_DEVELOPMENT,
        OpportunityCategory.GAME_DEVELOPMENT,
    }

    filtered = [
        opp
        for opp in opportunities
        if (opp.category.value if hasattr(opp.category, "value") else str(opp.category))
        in [c.value for c in dev_bounty_categories]
    ]

    # Filter for platforms that support CoderAgent
    automatable = [
        opp
        for opp in filtered
        if (opp.platform.value if hasattr(opp.platform, "value") else str(opp.platform)).lower()
        in CODER_AGENT_PLATFORMS
    ]

    logger.info(f"Found {len(automatable)} automatable dev bounty opportunities")

    # Run automation
    automation_engine = DevBountyAutomationEngine()
    results = await automation_engine.automate_batch(automatable[: target or 5])

    # Summary
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    return {
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "results": [r.to_dict() for r in results],
    }


# Global instance
_dev_bounty_automation: DevBountyAutomationEngine | None = None


def get_dev_bounty_automation() -> DevBountyAutomationEngine:
    global _dev_bounty_automation
    if _dev_bounty_automation is None:
        _dev_bounty_automation = DevBountyAutomationEngine()
    return _dev_bounty_automation
