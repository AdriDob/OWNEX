"""Self-Healer Scheduler — Runs periodic scans and auto-fixes."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from core.scheduler.scheduler import get_core_scheduler
from cores.events.event_bus import get_event_bus
from cores.self_healer import (
    get_patch_generator,
    get_problem_detector,
    get_root_cause_analyzer,
    get_safe_deployer,
    get_solution_learner,
)
from cores.self_healer.models import (
    ApprovalRequired,
    FixPlan,
    HealerConfig,
    Problem,
)

logger = logging.getLogger("ownex.self_healer.scheduler")


class SelfHealerScheduler:
    """Runs periodic self-healing scans and executes auto-fixes."""

    def __init__(self, config: HealerConfig | None = None):
        self.config = config or HealerConfig()
        self.event_bus = get_event_bus()
        self.scheduler = get_core_scheduler()
        self._running = False
        self._scan_task: asyncio.Task | None = None
        self._fixes_in_progress = 0

        # Initialize components
        self.detector = get_problem_detector(config)
        self.analyzer = get_root_cause_analyzer()
        self.patcher = get_patch_generator()
        self.deployer = get_safe_deployer(config)
        self.learner = get_solution_learner()

    async def initialize(self) -> None:
        """Initialize all components."""
        await self.analyzer.initialize()
        logger.info("Self-Healer Scheduler initialized")

    def start(self) -> None:
        """Start the periodic scan loop."""
        if self._running:
            return

        self._running = True
        self._scan_task = asyncio.create_task(self._scan_loop())
        logger.info(f"Self-Healer Scheduler started (interval: {self.config.scan_interval_minutes} min)")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()
        logger.info("Self-Healer Scheduler stopped")

    async def _scan_loop(self) -> None:
        """Main scan loop."""
        while self._running:
            try:
                await self.run_scan_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scan cycle error: {e}")

            # Wait for next interval
            try:
                await asyncio.sleep(self.config.scan_interval_minutes * 60)
            except asyncio.CancelledError:
                break

    async def run_scan_cycle(self) -> dict[str, Any]:
        """Run a single scan cycle: detect → diagnose → fix."""
        cycle_start = datetime.now(UTC)
        logger.info("Starting self-healer scan cycle")

        results = {
            "cycle_start": cycle_start.isoformat(),
            "problems_found": 0,
            "problems_diagnosed": 0,
            "fixes_attempted": 0,
            "fixes_succeeded": 0,
            "fixes_failed": 0,
            "errors": [],
        }

        try:
            # 1. Detect problems
            problems = await self.detector.scan()
            results["problems_found"] = len(problems)

            if not problems:
                logger.info("No problems detected")
                return results

            # 2. Process each problem (with concurrency limit)
            semaphore = asyncio.Semaphore(self.config.max_concurrent_fixes)

            async def process_problem(problem: Problem):
                async with semaphore:
                    return await self._process_problem(problem)

            tasks = [process_problem(p) for p in problems if p.is_active]
            problem_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(problem_results):
                if isinstance(result, Exception):
                    results["errors"].append(f"Problem {problems[i].id}: {result}")
                elif isinstance(result, dict):
                    results["problems_diagnosed"] += 1
                    if result.get("fix_attempted"):
                        results["fixes_attempted"] += 1
                        if result.get("fix_succeeded"):
                            results["fixes_succeeded"] += 1
                        else:
                            results["fixes_failed"] += 1

        except Exception as e:
            logger.error(f"Scan cycle error: {e}")
            results["errors"].append(str(e))

        results["cycle_end"] = datetime.now(UTC).isoformat()
        results["duration_seconds"] = (datetime.now(UTC) - cycle_start).total_seconds()

        logger.info(
            f"Scan cycle completed: {results['problems_found']} problems, "
            f"{results['fixes_succeeded']}/{results['fixes_attempted']} fixes succeeded"
        )
        return results

    async def _process_problem(self, problem: Problem) -> dict[str, Any]:
        """Process a single problem: diagnose → plan → fix."""
        result = {
            "problem_id": problem.id,
            "diagnosed": False,
            "fix_attempted": False,
            "fix_succeeded": False,
            "error": None,
        }

        try:
            # Check if we've seen this problem recently (avoid duplicate fixes)
            if await self._is_recently_fixed(problem):
                logger.info(f"Skipping recently fixed problem: {problem.id}")
                return result

            # 1. Diagnose
            diagnosis = await self.analyzer.analyze(problem)
            result["diagnosed"] = True
            result["diagnosis_id"] = diagnosis.id

            # 3. Create fix plan
            plan = await self._create_fix_plan(problem, diagnosis)
            result["plan_id"] = plan.id

            # 4. Check if approval needed
            if plan.approval_required in self.config.require_approval_for:
                if not self.config.auto_approve_low_risk or plan.approval_required != ApprovalRequired.LOW_RISK:
                    logger.info(f"Fix requires approval: {plan.id} ({plan.approval_required.value})")
                    # Queue for human approval (could notify via event bus)
                    self.event_bus.publish(
                        "self_healer:approval_needed",
                        **{
                            "problem_id": problem.id,
                            "plan_id": plan.id,
                            "approval_required": plan.approval_required.value,
                        },
                    )
                    result["awaiting_approval"] = True
                    return result

            # 5. Generate patch
            patch = await self.patcher.generate_patch(
                plan,
                excluded_paths=self.config.excluded_paths,
            )
            result["patch_id"] = patch.id

            # 6. Deploy
            result["fix_attempted"] = True
            deployment = await self.deployer.deploy(
                patch,
                environment="production",
                require_approval=False,  # Already checked above
            )

            if deployment.status.value == "completed":
                result["fix_succeeded"] = True
                result["deployment_id"] = deployment.id
            else:
                result["fix_succeeded"] = False
                result["error"] = f"Deployment failed: {deployment.rollback_reason}"

        except Exception as e:
            logger.error(f"Error processing problem {problem.id}: {e}")
            result["error"] = str(e)

        return result

    async def _is_recently_fixed(self, problem: Problem) -> bool:
        """Check if a similar problem was recently fixed."""
        # Check learner for recent similar fixes
        similar = self.learner.get_similar_successful_fixes(problem.category.value, limit=3)
        if similar:
            # Check if any was fixed in the last hour
            for fix in similar:
                ts = fix.get("timestamp", "")
                try:
                    fix_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if (datetime.now(UTC) - fix_time).total_seconds() < 3600:
                        return True
                except Exception:
                    pass
        return False

    async def _create_fix_plan(self, problem: Problem, diagnosis) -> FixPlan:
        """Create a fix plan from diagnosis."""
        from cores.self_healer.models import FixPlan

        # Determine files to modify based on affected components
        files_to_modify = []
        for component in diagnosis.contributing_factors:
            # Map components to likely files
            if "config" in component.lower():
                files_to_modify.extend(["config.yaml", "pyproject.toml"])
            elif "database" in component.lower():
                files_to_modify.extend(["database/db.py"])
            elif "scheduler" in component.lower():
                files_to_modify.extend(["core/scheduler/", "cores/scheduler/"])
            elif "memory" in component.lower():
                files_to_modify.extend(["cores/memory/", "core/memory/"])

        # Remove duplicates and filter excluded
        files_to_modify = list(set(files_to_modify))

        plan = FixPlan(
            id=f"plan_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
            diagnosis_id=diagnosis.id,
            strategy=diagnosis.suggested_strategy,
            description=f"Auto-fix for: {problem.title}",
            steps=[
                f"Diagnose: {diagnosis.root_cause}",
                f"Apply {diagnosis.suggested_strategy.value} to fix",
                "Run tests",
                "Deploy with canary",
                "Verify health",
            ],
            files_to_modify=files_to_modify[:5],  # Limit to 5 files
            config_changes={},
            tests_to_add=[f"test_fix_for_{problem.category.value}"],
            rollback_plan="Revert via VersionBackupSystem or git reset --hard",
            approval_required=ApprovalRequired.LOW_RISK
            if diagnosis.suggested_strategy in ["config_change", "restart_service"]
            else ApprovalRequired.HIGH_RISK,
            estimated_duration_minutes=30,
        )
        return plan

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "config": {
                "scan_interval_minutes": self.config.scan_interval_minutes,
                "max_concurrent_fixes": self.config.max_concurrent_fixes,
                "auto_approve_low_risk": self.config.auto_approve_low_risk,
            },
            "fixes_in_progress": self._fixes_in_progress,
            "components": {
                "detector": self.detector.get_status(),
                "analyzer": self.analyzer.get_status(),
                "deployer": self.deployer.get_status(),
                "learner": self.learner.get_learning_stats(),
            },
        }

    async def trigger_manual_scan(self) -> dict[str, Any]:
        """Trigger an immediate scan cycle."""
        return await self.run_scan_cycle()


# Singleton
_self_healer_scheduler: SelfHealerScheduler | None = None


def get_self_healer_scheduler(config: HealerConfig | None = None) -> SelfHealerScheduler:
    global _self_healer_scheduler
    if _self_healer_scheduler is None:
        _self_healer_scheduler = SelfHealerScheduler(config)
    return _self_healer_scheduler
