#!/usr/bin/env python3
"""OWNEX End-to-End Workflow Connector.

Connects the full pipeline: source discovery → zero-barrier eligibility
assessment → earnings tracking → income multiplication → investment deployment.

This is the orchestration layer that ties together all the components built
in this session into a coherent user journey.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger("ownex.workflow_connector")


class WorkflowStage(Enum):
    """Stages in the end-to-end workflow."""

    DISCOVERY = "discovery"  # Source discovery
    ELIGIBILITY = "eligibility"  # Zero-barrier assessment
    EARNINGS = "earnings"  # Earnings tracking
    INVESTMENT = "investment"  # Investment deployment
    MULTIPLIER = "multiplier"  # Income compounding
    COMPLETE = "complete"  # Workflow complete


@dataclass
class WorkflowResult:
    """Result of a full workflow execution."""

    stage: WorkflowStage
    success: bool
    results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    execution_time: float = 0.0
    round_number: int = 1


@dataclass
class WorkflowContext:
    """Context passed between workflow stages."""

    user_id: str
    source_id: str | None = None
    opportunity_id: str | None = None
    daily_earnings: Decimal = Decimal("0")
    strategy: str = "moderate"
    reinvestment_rate: float = 0.3
    min_earnings_threshold: float = 10.0


class WorkflowConnector:
    """Orchestrates the end-to-end workflow across all OWNEX systems.

    Pipeline: Source Discovery → Zero-Barrier Eligibility → Earnings Tracking
    → Income Multiplication → Investment Deployment
    """

    def __init__(self):
        # Initialize core engines
        from cores.income_multiplier import IncomeMultiplier
        from cores.workflow.orchestrator import WorkflowOrchestrator
        from cores.zero_barrier_eligibility import get_eligibility_engine

        self.eligibility_engine = get_eligibility_engine()
        self.accessibility_engine = None  # initialized on demand

        # Canonical orchestration: every workflow execution is registered as a
        # workflow in the single canonical WorkflowOrchestrator (no parallel pipeline).
        self.orchestrator = WorkflowOrchestrator()
        self._workflow_id: str | None = None

        # Income multiplier with moderate strategy by default (real config class)
        from cores.income_multiplier import MultiplierConfig, MultiplierStrategy

        multiplier_config = MultiplierConfig(
            strategy=MultiplierStrategy.MODERATE,
            allocation_percentages={},  # strategy defaults
            reinvestment_rate=0.3,
            min_earnings_threshold=10.0,
            max_compound_rounds=10,
            risk_tolerance="medium",
            auto_rebalance=True,
        )
        self.income_multiplier = IncomeMultiplier(multiplier_config)

        # Workflow state
        self._workflow_history: list[WorkflowResult] = []
        self._current_context: WorkflowContext | None = None

    def set_context(self, context: WorkflowContext) -> None:
        """Set the workflow context and register the canonical workflow.

        Args:
            context: WorkflowContext with user configuration
        """
        self._current_context = context
        self._workflow_id = self._create_canonical_workflow(context)
        logger.info(
            f"[WORKFLOW] Context set: user={context.user_id}, "
            f"strategy={context.strategy}, earnings_threshold=${context.min_earnings_threshold}, "
            f"canonical_workflow={self._workflow_id}"
        )

    # Canonical stage names, in loop order.
    CANONICAL_STAGES: tuple[str, ...] = (
        "discover",
        "evaluate",
        "execute",
        "verify",
        "earn",
        "capital",
    )

    def _create_canonical_workflow(self, context: WorkflowContext) -> str:
        """Create the DISCOVER→EVALUATE→EXECUTE→VERIFY→EARN→CAPITAL workflow.

        Returns:
            The canonical workflow id.
        """
        from cores.workflow.engine import WorkflowTask

        names = {
            "discover": "Source Discovery",
            "evaluate": "Zero-Barrier Evaluation",
            "execute": "Earnings Execution",
            "verify": "Earnings Verification",
            "earn": "Earnings Recognition",
            "capital": "Capital Deployment",
        }
        tasks: list[WorkflowTask] = []
        previous: str | None = None
        for stage in self.CANONICAL_STAGES:
            tasks.append(
                WorkflowTask(
                    id=stage,
                    name=names[stage],
                    agent_id="ownex_engine",
                    description=f"OWNEX canonical loop stage: {stage}",
                    dependencies=[previous] if previous else [],
                )
            )
            previous = stage

        workflow = self.orchestrator.create_workflow(
            name=f"user_{context.user_id}_workflow",
            description=f"OWNEX loop for {context.user_id}",
            tasks=tasks,
            metadata={
                "user_id": context.user_id,
                "source_id": context.source_id,
                "strategy": context.strategy,
            },
        )
        return workflow.id

    def _advance_canonical(self, stage: WorkflowStage, ok: bool, payload: dict[str, Any]) -> None:
        """Mark the canonical task matching a connector stage as done.

        Keeps the canonical orchestrator in sync with the connector's stages so
        there is exactly one workflow of record.
        """
        if not self._workflow_id:
            return

        mapping = {
            WorkflowStage.DISCOVERY: "discover",
            WorkflowStage.ELIGIBILITY: "evaluate",
            WorkflowStage.EARNINGS: "execute",
            WorkflowStage.MULTIPLIER: "earn",
            WorkflowStage.INVESTMENT: "capital",
        }
        task_id = mapping.get(stage)
        if not task_id:
            return

        try:
            workflow = self.orchestrator.get_workflow(self._workflow_id)
            if workflow is None:
                return
            if workflow.status.value == "pending":
                self.orchestrator.start_workflow(self._workflow_id)

            # Canonical progress is monotonic: reaching a stage completes every
            # earlier stage that was not explicitly reported by the connector.
            target_index = self.CANONICAL_STAGES.index(task_id)
            for canonical_id in self.CANONICAL_STAGES[: target_index + 1]:
                task = workflow.get_task(canonical_id)
                if task is None or task.status.value in ("completed", "failed", "skipped"):
                    continue
                if task.status.value == "pending":
                    self.orchestrator._assign_and_start_task(self._workflow_id, canonical_id, "ownex_engine")
                is_last = canonical_id == task_id
                if is_last and not ok:
                    self.orchestrator.fail_task(self._workflow_id, canonical_id, "stage failed")
                    break
                self.orchestrator.complete_task(self._workflow_id, canonical_id, payload if is_last else {"stage": canonical_id})
        except Exception as exc:  # canonical tracking must never break the pipeline
            logger.warning(f"[WORKFLOW] canonical sync failed for {stage.value}: {exc}")

    def get_context(self) -> WorkflowContext | None:
        """Get current workflow context."""
        return self._current_context

    async def execute_full_pipeline(self, source_data: dict[str, Any], daily_earnings: float | Decimal = 0, strategy: str = "moderate") -> WorkflowResult:
        """Execute the full end-to-end workflow.

        Pipeline stages:
        1. Discovery & Eligibility Assessment
        2. Earnings Tracking
        3. Income Multiplication
        4. Investment Readiness

        Args:
            source_data: Source metadata for eligibility assessment
            daily_earnings: Daily earnings amount (USD)
            strategy: Multiplier strategy (conservative/moderate/aggressive/compound)

        Returns:
            WorkflowResult with all stage results
        """
        start_time = datetime.now()
        result = WorkflowResult(stage=WorkflowStage.DISCOVERY, success=False)

        try:
            # ── Stage 1: Discovery & Eligibility ──────────────────────
            logger.info("[WORKFLOW] Stage 1: Discovery & Eligibility Assessment")

            source_id = source_data.get("source_id", "unknown_source")

            # Assess zero-barrier eligibility
            assessment = self.eligibility_engine.assess_source(source_id, source_data)
            result.results["eligibility_assessment"] = {
                "source_id": assessment.source_id,
                "eligibility": assessment.eligibility.value,
                "barriers": [b.value for b in assessment.barriers_identified],
                "recommended_actions": assessment.recommended_actions,
                "difficulty": assessment.difficulty,
                "estimated_earnings_potential": assessment.estimated_earnings_potential,
                "onboarding_time_minutes": assessment.onboarding_time_minutes,
            }
            result.stage = WorkflowStage.ELIGIBILITY

            # Check if source is eligible
            from cores.zero_barrier_eligibility import EligibilityStatus

            if assessment.eligibility != EligibilityStatus.APPROVED:
                result.success = False
                result.errors.append(f"Source not zero-barrier eligible: {assessment.eligibility.value}")
                logger.warning(f"[WORKFLOW] Eligibility failed: {assessment.eligibility.value}")
                return self._finalize_result(result, start_time, "eligibility_blocked")

            logger.info(f"[WORKFLOW] Eligibility approved: {assessment.source_id}, estimated earnings: ${assessment.estimated_earnings_potential}/day")

            # ── Stage 2: Earnings Tracking ───────────────────────────
            logger.info("[WORKFLOW] Stage 2: Earnings Tracking")

            # Convert earnings to Decimal
            earnings_decimal = Decimal(str(daily_earnings)) if daily_earnings else assessment.estimated_earnings_potential

            # Create workflow context for subsequent stages
            context = WorkflowContext(
                user_id=source_data.get("user_id", "unknown_user"),
                source_id=source_id,
                daily_earnings=earnings_decimal,
                strategy=strategy,
                reinvestment_rate=0.3,  # default
                min_earnings_threshold=10.0,
            )
            # Reuse the canonical workflow if one is already registered for this
            # execution instead of creating a second one.
            if self._workflow_id is None:
                self.set_context(context)
            else:
                self._current_context = context

            result.results["earnings_tracking"] = {
                "daily_earnings": float(earnings_decimal),
                "currency": "USD",
                "source": assessment.metadata.get("platform", "unknown"),
            }
            result.stage = WorkflowStage.EARNINGS

            # ── Stage 3: Income Multiplication ───────────────────────
            logger.info("[WORKFLOW] Stage 3: Income Multiplication")

            # Calculate multiplier effect
            mult_result = self._calculate_multiplier(
                daily_earnings=earnings_decimal,
                strategy=strategy,
                round_number=1,
            )

            result.results["income_multiplier"] = {
                "strategy": mult_result.strategy.value,
                "earnings_processed": float(mult_result.earnings_processed),
                "new_earnings_capacity": float(mult_result.new_earnings_capacity),
                "reinvested_amount": float(mult_result.reinvested_amount),
                "total_multiplier_effect": float(mult_result.earnings_processed + mult_result.new_earnings_capacity),
                "allocation_breakdown": {k.value: float(v) for k, v in mult_result.allocation.items()},
            }
            result.stage = WorkflowStage.MULTIPLIER

            # Check if multiplication was applied
            if mult_result.new_earnings_capacity == 0:
                result.errors.append("Multiplier threshold not met; no multiplication applied")
                logger.warning("[WORKFLOW] Multiplier threshold not met")

            # ── Stage 4: Investment Readiness ────────────────────────
            logger.info("[WORKFLOW] Stage 4: Investment Readiness")

            # Prepare investment allocation based on multiplier results
            allocation = mult_result.allocation

            investment_prep = {
                "allocations": {k.value: float(v) for k, v in allocation.items()},
                "total_reinvested": float(mult_result.reinvested_amount),
                "new_capital_deployable": float(mult_result.new_earnings_capacity),
                "strategy": mult_result.strategy.value,
                "ready_to_deploy": mult_result.new_earnings_capacity > 0,
            }
            result.results["investment_readiness"] = investment_prep
            result.stage = WorkflowStage.INVESTMENT

            # All stages passed
            result.success = True
            total_capacity = float(
                mult_result.earnings_processed + mult_result.new_earnings_capacity
            )
            multiplier_factor = (
                total_capacity / float(earnings_decimal) if float(earnings_decimal) else 0.0
            )
            logger.info(
                f"[WORKFLOW] Full pipeline complete: ${earnings_decimal} → "
                f"${total_capacity:.2f} (x{multiplier_factor:.2f}x)"
            )

        except Exception as e:
            logger.error(f"[WORKFLOW] Pipeline error: {e}", exc_info=True)
            result.success = False
            result.errors.append(str(e))

        return self._finalize_result(result, start_time, "full_pipeline")

    async def execute_earnings_to_multiplier(self, daily_earnings: float | Decimal, strategy: str = "moderate") -> WorkflowResult:
        """Execute stages 2-3: earnings tracking → income multiplication.

        Useful when eligibility has already been assessed.
        """
        start_time = datetime.now()
        result = WorkflowResult(stage=WorkflowStage.EARNINGS, success=False)

        try:
            # Earnings tracking
            earnings_decimal = Decimal(str(daily_earnings)) if daily_earnings else Decimal("0")

            result.results["earnings_tracking"] = {
                "daily_earnings": float(earnings_decimal),
                "currency": "USD",
            }
            result.stage = WorkflowStage.EARNINGS

            # Income multiplication
            mult_result = self._calculate_multiplier(
                daily_earnings=earnings_decimal,
                strategy=strategy,
                round_number=self._get_current_round() + 1,
            )

            result.results["income_multiplier"] = {
                "strategy": mult_result.strategy.value,
                "earnings_processed": float(mult_result.earnings_processed),
                "new_earnings_capacity": float(mult_result.new_earnings_capacity),
                "reinvested_amount": float(mult_result.reinvested_amount),
                "total_multiplier_effect": float(mult_result.earnings_processed + mult_result.new_earnings_capacity),
                "allocation_breakdown": {k.value: float(v) for k, v in mult_result.allocation.items()},
            }
            result.stage = WorkflowStage.MULTIPLIER
            result.success = True

            logger.info(f"[WORKFLOW] Earnings→Multiplier: ${earnings_decimal} → ${mult_result.earnings_processed + mult_result.new_earnings_capacity}")

        except Exception as e:
            logger.error(f"[WORKFLOW] Earnings→Multiplier error: {e}", exc_info=True)
            result.success = False
            result.errors.append(str(e))

        return self._finalize_result(result, start_time, "earnings_to_multiplier")

    async def execute_multiplier_to_investment(self, allocation_targets: dict[str, float] | None = None) -> WorkflowResult:
        """Execute stage 3-4: income multiplication → investment deployment.

        Uses the last multiplier results to prepare investment allocations.
        """
        start_time = datetime.now()
        result = WorkflowResult(stage=WorkflowStage.MULTIPLIER, success=False)

        try:
            # Get current multiplier state
            summary = self.income_multiplier.get_compound_summary()

            total_reinvested = summary.get("total_reinvested", 0)
            total_earnings_multiplied = summary.get("total_earnings_multiplied", 0)

            # Prepare investment allocations
            if allocation_targets is None:
                # Use default moderate allocations
                allocation_targets = {
                    "crypto_trading": 0.30,
                    "defi_yield": 0.25,
                    "bug_bounty_boost": 0.20,
                    "dev_boost": 0.15,
                    "reinvest": 0.10,
                }

            # Normalize allocations
            total_weight = sum(allocation_targets.values())
            normalized_allocations = {k: v / total_weight for k, v in allocation_targets.items()}

            result.results["investment_allocations"] = {
                "reinvested_since_origin": total_reinvested,
                "total_earnings_multiplied": total_earnings_multiplied,
                "allocations": normalized_allocations,
                "allocation_count": len(normalized_allocations),
            }
            result.stage = WorkflowStage.INVESTMENT
            result.success = True

            logger.info(
                f"[WORKFLOW] Investment readiness: ${total_reinvested} reinvested, "
                f"${total_earnings_multiplied} multiplied across {len(normalized_allocations)} streams"
            )

        except Exception as e:
            logger.error(f"[WORKFLOW] Multiplier→Investment error: {e}", exc_info=True)
            result.success = False
            result.errors.append(str(e))

        return self._finalize_result(result, start_time, "multiplier_to_investment")

    def _build_multiplier(self, strategy: str):
        """Build an IncomeMultiplier configured for the requested strategy.

        The multiplier API takes configuration at construction time, so the
        strategy must be applied to the config rather than to each call.
        """
        from cores.income_multiplier import (
            IncomeMultiplier,
            MultiplierConfig,
            MultiplierStrategy,
        )

        try:
            strat = MultiplierStrategy(strategy)
        except ValueError:
            logger.warning(f"[WORKFLOW] Unknown strategy '{strategy}', using moderate")
            strat = MultiplierStrategy.MODERATE

        base = self.income_multiplier.config
        config = MultiplierConfig(
            strategy=strat,
            allocation_percentages=dict(base.allocation_percentages or {}),
            reinvestment_rate=base.reinvestment_rate,
            min_earnings_threshold=base.min_earnings_threshold,
            max_compound_rounds=base.max_compound_rounds,
            risk_tolerance=base.risk_tolerance,
            auto_rebalance=base.auto_rebalance,
            is_simulation=base.is_simulation,
            classified_earnings_flow=base.classified_earnings_flow,
        )
        return IncomeMultiplier(config)

    def _calculate_multiplier(self, daily_earnings: Decimal, strategy: str, round_number: int):
        """Run income multiplication using the real IncomeMultiplier API."""
        multiplier = self._build_multiplier(strategy)
        state = multiplier.initialize_compound_state(round_number=round_number)
        return multiplier.calculate_multiplier(daily_earnings, state)

    def _get_current_round(self) -> int:
        """Get the current compounding round number."""
        summary = self.income_multiplier.get_compound_summary()
        return summary.get("current_round", 0)

    def _finalize_result(self, result: WorkflowResult, start_time: datetime, trigger: str) -> WorkflowResult:
        """Finalize the workflow result with execution time and history tracking.

        Args:
            result: WorkflowResult to finalize
            start_time: Workflow start timestamp
            trigger: What triggered this workflow execution

        Returns:
            Finalized WorkflowResult
        """
        execution_time = (datetime.now() - start_time).total_seconds()
        result.execution_time = execution_time

        # Register the stage outcome in the canonical orchestrator
        self._advance_canonical(result.stage, result.success, dict(result.results))

        # Add to history
        self._workflow_history.append(result)

        # Keep history manageable (last 50 executions)
        if len(self._workflow_history) > 50:
            self._workflow_history = self._workflow_history[-50:]

        # Log summary
        status_emoji = "✅" if result.success else "❌"
        logger.info(
            f"{status_emoji} [WORKFLOW] {trigger}: {result.stage.value} | success={result.success} | time={execution_time:.2f}s | errors={len(result.errors)}"
        )

        if result.errors:
            for error in result.errors:
                logger.warning(f"[WORKFLOW] {trigger} error: {error}")

        return result

    def get_workflow_history(self, stages: list[WorkflowStage] | None = None) -> list[WorkflowResult]:
        """Get workflow execution history.

        Args:
            stages: Filter by specific stages (optional)

        Returns:
            List of WorkflowResult objects
        """
        if stages is None:
            return self._workflow_history
        return [r for r in self._workflow_history if r.stage in stages]

    def get_workflow_summary(self) -> dict[str, Any]:
        """Get workflow execution summary.

        Returns:
            Dictionary with workflow statistics
        """
        total_executions = len(self._workflow_history)
        if total_executions == 0:
            return {
                "total_executions": 0,
                "success_rate": 0,
                "stages_completed": {},
                "average_execution_time": 0,
            }

        successful = sum(1 for r in self._workflow_history if r.success)
        success_rate = successful / total_executions

        # Count stages completed
        stages_completed: dict[str, int] = {}
        for r in self._workflow_history:
            stage_name = r.stage.value
            stages_completed[stage_name] = stages_completed.get(stage_name, 0) + 1

        avg_execution_time = sum(r.execution_time for r in self._workflow_history) / total_executions

        return {
            "total_executions": total_executions,
            "success_rate": round(success_rate, 2),
            "stages_completed": stages_completed,
            "average_execution_time": round(avg_execution_time, 2),
            "latest_round": self._get_current_round(),
        }


# Convenience function for single workflow execution
async def run_full_workflow(
    source_data: dict[str, Any],
    daily_earnings: float | Decimal = 0,
    strategy: str = "moderate",
    user_id: str = "default_user",
) -> WorkflowResult:
    """Run the full end-to-end workflow with one function call.

    Args:
        source_data: Source metadata for eligibility assessment
        daily_earnings: Daily earnings amount (USD)
        strategy: Multiplier strategy
        user_id: User identifier

    Returns:
        WorkflowResult with all stage results
    """
    connector = WorkflowConnector()
    context = WorkflowContext(user_id=user_id)
    connector.set_context(context)

    return await connector.execute_full_pipeline(source_data, daily_earnings, strategy)
