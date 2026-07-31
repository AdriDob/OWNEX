"""Autonomous Workflow Engine — Orchestrates discover→select→plan→execute→learn loop."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.opportunity.adapters import fetch_all_opportunities
from core.opportunity.executors import BaseExecutor
from core.opportunity.models import PersonalHistory
from core.opportunity.scorer import score_opportunity


@dataclass
class WorkPlan:
    """Execution plan for an opportunity."""

    opportunity_id: str
    platform: str
    actions: list[dict[str, Any]]  # [{"action": "claim_issue", "params": {...}}, ...]
    estimated_effort_hours: float
    estimated_reward: float
    confidence: float
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class ExecutionResult:
    """Result of executing a work plan."""

    plan: WorkPlan
    success: bool
    action_results: list[ExecutionResult]
    total_time_seconds: float
    reward_earned: float = 0.0
    error: str | None = None
    completed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AutonomousWorkflow:
    """
    Main autonomous workflow engine.

    Loop:
    1. DISCOVER — fetch_all_opportunities()
    2. SELECT — score + filter + rank → pick best
    3. PLAN — create WorkPlan with executable actions
    4. EXECUTE — run actions via executors/browser agent
    5. LEARN — record outcome, update personal history
    """

    def __init__(
        self,
        personal: PersonalHistory | None = None,
        executors: dict[str, BaseExecutor] | None = None,
        browser_agent: Any = None,
        config: dict[str, Any] | None = None,
    ):
        self.personal = personal
        self.executors = executors or {}
        self.browser_agent = browser_agent
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.min_score_threshold = self.config.get("min_score_threshold", 60.0)
        self.max_concurrent = self.config.get("max_concurrent", 1)
        self.dry_run = self.config.get("dry_run", False)
        self.execution_history: list[ExecutionResult] = []

    async def run_cycle(self) -> list[ExecutionResult]:
        """Run one full autonomous cycle."""
        if not self.enabled:
            return []

        # 1. DISCOVER
        opportunities = await fetch_all_opportunities(personal=self.personal)

        # 2. SELECT — score and filter
        scored = []
        for opp in opportunities:
            scored_opp = score_opportunity(
                opp_id=opp.id,
                name=opp.name,
                cycle=opp.cycle,
                source_type=opp.source_type,
                source_name=opp.source_name,
                reward=opp.reward,
                effort_hours=opp.effort_hours,
                platform=opp.platform,
                technology_tags=opp.tags,
                url=opp.url,
                created_at=opp.created_at,
                personal=self.personal,
                original=opp.metadata,
            )
            if scored_opp.score.overall >= self.min_score_threshold:
                scored.append(scored_opp)

        scored.sort(key=lambda x: -x.score.overall)

        if not scored:
            return []

        # 3. PLAN — create work plans for top opportunities
        plans = []
        for opp in scored[: self.max_concurrent]:
            plan = await self._create_plan(opp)
            if plan:
                plans.append(plan)

        # 4. EXECUTE — run plans
        results = []
        for plan in plans:
            if self.dry_run:
                result = ExecutionResult(
                    plan=plan,
                    success=True,
                    action_results=[],
                    total_time_seconds=0,
                    reward_earned=0,
                    error="DRY RUN - not executed",
                )
            else:
                result = await self._execute_plan(plan)
            results.append(result)
            self.execution_history.append(result)

            # Learn from result
            await self._learn_from_result(result)

        return results

    async def _create_plan(self, scored_opp) -> WorkPlan | None:
        """Create executable work plan from scored opportunity."""
        platform = scored_opp.platform

        # Platform-specific planning
        if platform in ["algora", "opire", "opyre", "issuehunt", "issuehand"]:
            return await self._plan_oss_bounty(scored_opp)
        elif platform == "freelancer":
            return await self._plan_freelancer(scored_opp)
        elif platform in ["dataannotation", "outlier", "mindrift", "remotasks"]:
            return await self._plan_ai_work(scored_opp)
        elif platform == "linkedin":
            return await self._plan_linkedin(scored_opp)
        elif platform == "opencollective":
            return await self._plan_opencollective(scored_opp)

        return None

    async def _plan_oss_bounty(self, opp) -> WorkPlan | None:
        """Plan for OSS bounty platforms (Algora, Opire, IssueHunt)."""
        # Extract repo and issue from URL or metadata
        metadata = opp.original or {}
        repo = metadata.get("repository") or metadata.get("repo")
        issue_number = metadata.get("issue_number")
        bounty_id = metadata.get("bounty_id") or opp.id

        if not repo or not issue_number:
            return None

        actions = [
            {"action": "claim_issue", "params": {"bounty_id": bounty_id, "repo": repo, "issue_number": issue_number}},
            # The next actions (create_pr, submit_pr) will be filled in after claim succeeds
            # This is a template - actual PR creation happens during execution
        ]

        return WorkPlan(
            opportunity_id=opp.id,
            platform=opp.platform,
            actions=actions,
            estimated_effort_hours=opp.effort_hours,
            estimated_reward=opp.reward,
            confidence=min(opp.score.overall / 100.0, 1.0),
        )

    async def _plan_freelancer(self, opp) -> WorkPlan | None:
        """Plan for Freelancer.com projects."""
        metadata = opp.original or {}
        project_id = metadata.get("project_id") or opp.id.split("_")[-1]

        actions = [
            {
                "action": "bid_on_project",
                "params": {
                    "project_id": project_id,
                    "bid_amount": opp.reward * 0.9,  # Bid 90% of budget
                    "period": 7,  # 7 days
                    "description": f"Automated bid for {opp.name}",
                    "milestone_percentage": 100,
                },
            }
        ]

        return WorkPlan(
            opportunity_id=opp.id,
            platform=opp.platform,
            actions=actions,
            estimated_effort_hours=opp.effort_hours,
            estimated_reward=opp.reward,
            confidence=min(opp.score.overall / 100.0, 0.8),  # Lower confidence for bids
        )

    async def _plan_ai_work(self, opp) -> WorkPlan | None:
        """Plan for AI work platforms (DataAnnotation, Outlier, etc.)."""
        metadata = opp.original or {}
        task_url = metadata.get("task_url") or opp.url

        if not task_url:
            return None

        actions = [
            {"action": "claim_task", "params": {"task_url": task_url}},
        ]

        return WorkPlan(
            opportunity_id=opp.id,
            platform=opp.platform,
            actions=actions,
            estimated_effort_hours=opp.effort_hours,
            estimated_reward=opp.reward,
            confidence=min(opp.score.overall / 100.0, 0.9),
        )

    async def _plan_linkedin(self, opp) -> WorkPlan | None:
        """Plan for LinkedIn Easy Apply."""
        metadata = opp.original or {}
        job_url = metadata.get("apply_url") or opp.url

        if not job_url:
            return None

        actions = [
            {"action": "easy_apply", "params": {"job_url": job_url}},
        ]

        return WorkPlan(
            opportunity_id=opp.id,
            platform=opp.platform,
            actions=actions,
            estimated_effort_hours=opp.effort_hours,
            estimated_reward=opp.reward,
            confidence=min(opp.score.overall / 100.0, 0.5),  # Low confidence for job apps
        )

    async def _plan_opencollective(self, opp) -> WorkPlan | None:
        """Plan for Open Collective contributions."""
        # Usually just funding - not executable work
        return None

    async def _execute_plan(self, plan: WorkPlan) -> ExecutionResult:
        """Execute a work plan using appropriate executors."""
        if self.dry_run:
            return ExecutionResult(
                plan=plan,
                success=True,
                action_results=[],
                total_time_seconds=0,
                reward_earned=0,
                error="DRY RUN - not executed",
            )

        start_time = time.time()
        action_results = []
        reward_earned = 0.0

        executor = self.executors.get(plan.platform)
        if not executor:
            return ExecutionResult(
                plan=plan,
                success=False,
                action_results=[],
                total_time_seconds=time.time() - start_time,
                error=f"No executor for platform: {plan.platform}",
            )

        for action_spec in plan.actions:
            action = action_spec["action"]
            params = action_spec["params"]

            # Execute via platform executor
            result = await executor.execute(action, **params)
            action_results.append(result)

            if not result.success:
                # Stop on first failure
                return ExecutionResult(
                    plan=plan,
                    success=False,
                    action_results=action_results,
                    total_time_seconds=time.time() - start_time,
                    error=f"Action {action} failed: {result.error}",
                )

            # If claim succeeded, continue with next steps (PR creation, etc.)
            if action == "claim_issue" and result.data:
                # Dynamically add PR creation step
                # This would be filled in by CoderAgent in real implementation
                pass

            if action in ["submit_pr", "submit_deliverable"] and result.data:
                reward_earned = plan.estimated_reward

        return ExecutionResult(
            plan=plan,
            success=True,
            action_results=action_results,
            total_time_seconds=time.time() - start_time,
            reward_earned=reward_earned,
        )

    async def _learn_from_result(self, result: ExecutionResult) -> None:
        """Update personal history and learning from execution result."""
        if not self.personal:
            return

        # Record outcome for VerdictLearner / RevenueIntelligence
        {
            "opportunity_id": result.plan.opportunity_id,
            "platform": result.plan.platform,
            "success": result.success,
            "reward_earned": result.reward_earned,
            "effort_hours": result.total_time_seconds / 3600,
            "confidence": result.plan.confidence,
            "timestamp": result.completed_at,
        }

        # This would feed into the learning system
        # self.personal.record_execution(outcome)
        pass

    async def run_continuous(self, interval_seconds: int = 3600) -> None:
        """Run autonomous cycles continuously."""
        while self.enabled:
            try:
                results = await self.run_cycle()
                if results:
                    print(f"[AutonomousWorkflow] Cycle completed: {len(results)} plans executed")
                    for r in results:
                        status = "✅" if r.success else "❌"
                        print(f"  {status} {r.plan.platform} - {r.plan.opportunity_id} (${r.reward_earned:.2f})")
                else:
                    print("[AutonomousWorkflow] No opportunities met threshold")
            except Exception as e:
                print(f"[AutonomousWorkflow] Cycle error: {e}")

            await asyncio.sleep(interval_seconds)


# Factory function for easy instantiation
async def create_autonomous_workflow(
    personal: PersonalHistory | None = None,
    config: dict[str, Any] | None = None,
) -> AutonomousWorkflow:
    """Create workflow with default executors."""
    from core.opportunity.executors.algora_executor import AlgoraExecutor
    from core.opportunity.executors.freelancer_executor import FreelancerExecutor

    executors = {
        "algora": AlgoraExecutor(config.get("algora") if config else None),
        "freelancer": FreelancerExecutor(config.get("freelancer") if config else None),
        # Add more as implemented
    }

    return AutonomousWorkflow(
        personal=personal,
        executors=executors,
        config=config or {},
    )
