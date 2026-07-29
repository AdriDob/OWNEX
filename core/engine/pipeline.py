"""Execution Pipeline — Plan → Prepare → Execute.

Extends the existing v5 execution infrastructure with structured planning
and preparation layers. PipelineEngine v5 is preserved; this adds the
orchestration layer around it.
"""
from __future__ import annotations

import logging
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.engine.base import Engine
from core.engine.classification import Opportunity

logger = logging.getLogger("ownex.pipeline")


# ── Core data types ────────────────────────────────────────────────


@dataclass
class PlanStep:
    """A single step in an execution plan."""

    id: str
    name: str
    description: str
    order: int
    capability: str                # capability ID needed
    estimated_minutes: int = 0
    depends_on: list[str] = field(default_factory=list)
    timeout_seconds: int = 300
    retry_count: int = 0
    retry_max: int = 3

    # Result placeholder
    result: Any = None
    status: str = "pending"        # pending | running | completed | failed | skipped
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class ExecutionPlan:
    """Full execution plan for an opportunity."""

    id: str
    opportunity_id: str
    steps: list[PlanStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_estimated_minutes: int = 0
    context_hash: str = ""
    status: str = "created"        # created | running | completed | failed

    def add_step(self, step: PlanStep) -> None:
        self.steps.append(step)
        self.total_estimated_minutes += step.estimated_minutes


@dataclass
class ExecutionResult:
    """Result of executing an opportunity."""

    success: bool
    error: str = ""
    plan: ExecutionPlan | None = None
    completed_steps: list[PlanStep] = field(default_factory=list)
    failed_step: PlanStep | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


# ── Plan templates by source_type ──────────────────────────────────


BUG_BOUNTY_PLAN = [
    PlanStep("recon", "Reconnaissance", "Gather intel: subdomains, endpoints, tech stack",
             order=1, capability="network_scanning", estimated_minutes=15),
    PlanStep("scope", "Scope Analysis", "Analyze program scope, rules, exclusions",
             order=2, capability="web_scraping", estimated_minutes=10),
    PlanStep("test", "Vulnerability Testing", "Systematic testing per methodology",
             order=3, capability="llm_reasoning", estimated_minutes=120),
    PlanStep("report", "Report Writing", "Write findings report with PoC",
             order=4, capability="llm_reasoning", estimated_minutes=30),
    PlanStep("submit", "Submission", "Submit finding to platform",
             order=5, capability="api_interaction", estimated_minutes=5),
]

DEV_BOUNTY_PLAN = [
    PlanStep("clone", "Clone Repository", "Clone repo and set up environment",
             order=1, capability="git_operations", estimated_minutes=5),
    PlanStep("understand", "Code Understanding", "Read existing code, understand patterns",
             order=2, capability="code_execution", estimated_minutes=30),
    PlanStep("implement", "Implementation", "Write code to solve the issue",
             order=3, capability="code_execution", estimated_minutes=120),
    PlanStep("test", "Testing", "Run tests, verify solution",
             order=4, capability="code_execution", estimated_minutes=15),
    PlanStep("submit", "Submit PR", "Create pull request with solution",
             order=5, capability="git_operations", estimated_minutes=5),
]

AI_WORK_PLAN = [
    PlanStep("analyze", "Analyze Task", "Read task description and requirements",
             order=1, capability="llm_reasoning", estimated_minutes=5),
    PlanStep("execute", "Execute Task", "Complete the AI work task",
             order=2, capability="code_execution", estimated_minutes=60),
    PlanStep("verify", "Verify Output", "Check quality before submission",
             order=3, capability="llm_reasoning", estimated_minutes=10),
    PlanStep("submit", "Submit", "Submit completed work",
             order=4, capability="api_interaction", estimated_minutes=2),
]

GENERIC_PLAN = [
    PlanStep("assess", "Assessment", "Assess the opportunity",
             order=1, capability="llm_reasoning", estimated_minutes=15),
    PlanStep("execute", "Execution", "Execute the work",
             order=2, capability="code_execution", estimated_minutes=60),
    PlanStep("submit", "Submission", "Submit results",
             order=3, capability="api_interaction", estimated_minutes=5),
]

PLAN_TEMPLATES: dict[str, list[PlanStep]] = {
    "bug_bounty": BUG_BOUNTY_PLAN,
    "dev_bounty": DEV_BOUNTY_PLAN,
    "ai_work": AI_WORK_PLAN,
}


# ── Planning Engine ────────────────────────────────────────────────


class PlanningEngine:
    """Given an opportunity + context, creates an execution plan.

    Uses templates for known opportunity types and generic for novel ones.
    """

    async def create_plan(
        self,
        opportunity: Opportunity,
        context_hash: str = "",
    ) -> ExecutionPlan:
        steps = PLAN_TEMPLATES.get(opportunity.source_type, GENERIC_PLAN)
        # Copy to avoid mutation
        plan_steps = [
            PlanStep(
                id=s.id,
                name=s.name,
                description=s.description,
                order=s.order,
                capability=s.capability,
                estimated_minutes=s.estimated_minutes,
                depends_on=list(s.depends_on),
                timeout_seconds=s.timeout_seconds,
                retry_max=s.retry_max,
            )
            for s in steps
        ]
        plan = ExecutionPlan(
            id=uuid.uuid4().hex[:16],
            opportunity_id=opportunity.id,
            steps=plan_steps,
            context_hash=context_hash,
        )
        plan.total_estimated_minutes = sum(s.estimated_minutes for s in plan_steps)
        return plan

    def get_template(self, source_type: str) -> list[PlanStep] | None:
        return PLAN_TEMPLATES.get(source_type)


# ── Preparation Engine ──────────────────────────────────────────────


class PreparationEngine:
    """Sets up the environment before execution.

    Idempotent — running it twice on the same step should be safe.
    """

    async def prepare(
        self,
        plan: ExecutionPlan,
        capability_engine: Any | None = None,
    ) -> dict[str, Any]:
        """Check environment for all steps in a plan.

        Returns preparation status per capability.
        """
        step_capabilities: set[str] = set()
        for step in plan.steps:
            step_capabilities.add(step.capability)
            if capability_engine:
                cap = capability_engine.get(step.capability)
                if cap and not cap.available:
                    logger.warning("Capability %s not available for step %s", cap.id, step.name)
                if cap and cap.requires_user:
                    logger.info("Step %s requires user interaction", step.name)

        results: dict[str, Any] = {}
        for cap_id in sorted(step_capabilities):
            result = await self._prepare_capability(cap_id)
            results[cap_id] = result

        return results

    async def _prepare_capability(self, capability_id: str) -> dict[str, Any]:
        checker = {
            "git_operations": self._check_git,
            "code_execution": self._check_code_exec,
            "web_scraping": self._check_http,
            "network_scanning": self._check_network_tools,
            "browser_automation": self._check_browser,
            "llm_reasoning": self._check_llm,
            "api_interaction": self._check_http,
        }
        check_fn = checker.get(capability_id)
        if check_fn:
            return await check_fn()
        return {"capability": capability_id, "status": "unknown", "available": True}

    async def _check_git(self) -> dict[str, Any]:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=10)
        ok = result.returncode == 0
        return {"capability": "git_operations", "status": "ready" if ok else "not_found",
                "version": result.stdout.strip() if ok else None, "available": ok}

    async def _check_code_exec(self) -> dict[str, Any]:
        return {"capability": "code_execution", "status": "ready",
                "version": sys.version, "available": True}

    async def _check_http(self) -> dict[str, Any]:
        try:
            import httpx  # noqa: F401
            return {"capability": "web_scraping", "status": "ready", "available": True}
        except ImportError:
            return {"capability": "web_scraping", "status": "missing_dependency", "available": False}

    async def _check_network_tools(self) -> dict[str, Any]:
        result = subprocess.run(["which", "nmap"], capture_output=True, text=True, timeout=10)
        ok = result.returncode == 0
        return {"capability": "network_scanning", "status": "ready" if ok else "not_found",
                "available": ok}

    async def _check_browser(self) -> dict[str, Any]:
        try:
            import playwright  # noqa: F401
            return {"capability": "browser_automation", "status": "ready", "available": True}
        except ImportError:
            return {"capability": "browser_automation", "status": "missing_dependency", "available": False}

    async def _check_llm(self) -> dict[str, Any]:
        return {"capability": "llm_reasoning", "status": "ready", "available": True}


# ── Execution Pipeline ─────────────────────────────────────────────


class ExecutionPipeline(Engine):
    """Orchestrates Plan → Prepare → Execute for an opportunity.

    Wraps existing v5 execution infrastructure. Each step is tracked
    with status, timing, and retry support.
    """

    name = "execution_pipeline"

    def __init__(
        self,
        dispatcher: Any | None = None,
        capability_engine: Any | None = None,
        context_engine: Any | None = None,
    ) -> None:
        super().__init__()
        self.planner = PlanningEngine()
        self.preparer = PreparationEngine()
        self.dispatcher = dispatcher
        self.capability_engine = capability_engine
        self.context_engine = context_engine
        self._running: set[str] = set()

    async def _execute_step_with_retry(
        self,
        step: PlanStep,
        opportunity: Opportunity,
    ) -> tuple[bool, dict[str, Any]]:
        """Execute a step with retry support. Returns (success, result_or_error)."""
        attempt = 0
        max_attempts = step.retry_max + 1  # first attempt + retries
        while attempt < max_attempts:
            attempt += 1
            if attempt > 1:
                logger.info("Retry %s (%d/%d)", step.name, attempt - 1, step.retry_max)
                step.retry_count += 1
                step.status = "running"

            try:
                result = await self._execute_step(step, opportunity)
                if result.get("success"):
                    return True, result
                # Log failure but retry
                logger.warning("Step %s failed (attempt %d/%d): %s",
                               step.name, attempt, max_attempts, result.get("error"))
            except Exception as e:
                logger.warning("Step %s raised exception (attempt %d/%d): %s",
                               step.name, attempt, max_attempts, e)
                if attempt >= max_attempts:
                    return False, {"error": str(e)}
                continue

        return False, {"error": f"Step {step.name} failed after {max_attempts} attempts"}

    async def execute(
        self,
        opportunity: Opportunity,
        plan: ExecutionPlan | None = None,
        context_hash: str = "",
    ) -> ExecutionResult:
        """Execute an opportunity from plan to completion."""
        started = datetime.now(timezone.utc)

        if plan is None:
            plan = await self.planner.create_plan(opportunity, context_hash)

        plan.status = "running"
        self._running.add(plan.id)

        # Prepare environment
        if self.capability_engine:
            prep_results = await self.preparer.prepare(plan, self.capability_engine)
            all_ready = all(r.get("available", False) for r in prep_results.values())
            if not all_ready:
                unavailable = [c for c, r in prep_results.items() if not r.get("available", False)]
                logger.warning("Unavailable capabilities for plan %s: %s", plan.id, unavailable)

        # Execute each step
        for step in plan.steps:
            step.started_at = datetime.now(timezone.utc)
            step.status = "running"

            logger.info("Step %d/%d: %s (%s)", step.order, len(plan.steps), step.name, step.capability)

            success, result = await self._execute_step_with_retry(step, opportunity)
            step.result = result

            if success:
                step.status = "completed"
                step.completed_at = datetime.now(timezone.utc)
            else:
                step.status = "failed"
                error = result.get("error", "Unknown error")
                plan.status = "failed"
                self._running.discard(plan.id)
                return ExecutionResult(
                    success=False,
                    plan=plan,
                    error=error,
                    completed_steps=[s for s in plan.steps if s.status == "completed"],
                    failed_step=step,
                    started_at=started,
                    completed_at=datetime.now(timezone.utc),
                )

        plan.status = "completed"
        self._running.discard(plan.id)
        return ExecutionResult(
            success=True,
            plan=plan,
            completed_steps=plan.steps,
            started_at=started,
            completed_at=datetime.now(timezone.utc),
        )

    async def _execute_step(
        self,
        step: PlanStep,
        opportunity: Opportunity,
    ) -> dict[str, Any]:
        """Execute a single plan step.

        Uses the existing CapabilityDispatcher if available,
        otherwise returns a stub result.
        """
        if self.dispatcher:
            try:
                result = self.dispatcher.execute(
                    step.capability,
                    {
                        "step_id": step.id,
                        "step_name": step.name,
                        "opportunity_id": opportunity.id,
                        "description": step.description,
                    },
                )
                return {"success": True, "data": result}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # Stub when no dispatcher — mark as succeeded for testing
        return {
            "success": True,
            "data": {"step": step.name, "capability": step.capability, "status": "stub"},
        }

    async def initialize(self) -> None:
        self._initialized = True

    async def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "name": self.name,
            "templates": list(PLAN_TEMPLATES.keys()),
            "running_plans": len(self._running),
        }
