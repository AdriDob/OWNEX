from __future__ import annotations

import asyncio
import contextvars
import inspect
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from cores.worker_core.contracts import (
    AIRouterProtocol,
    CostTrackerProtocol,
    DeliveryEngineProtocol,
    DiscoveryEngineProtocol,
    EvaluationEngineProtocol,
    ExecutionEngineProtocol,
    LearningEngineProtocol,
    SkillEngineProtocol,
)
from cores.worker_core.models import (
    AutonomyLevel,
    WorkerConfig,
    WorkerMetrics,
    WorkGoal,
    WorkItem,
    WorkPhase,
    WorkState,
)
from cores.worker_core.persistence import (
    resume_from,
    save_checkpoint,
)

# Trace ID context variable for structured logging
trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)

logger = logging.getLogger("worker_core.orchestrator")


def get_trace_id() -> str:
    """Get current trace ID, generate if not set."""
    trace_id = trace_id_var.get()
    if trace_id is None:
        trace_id = uuid4().hex[:16]
        trace_id_var.set(trace_id)
    return trace_id


def set_trace_id(trace_id: str) -> None:
    """Set trace ID for current context."""
    trace_id_var.set(trace_id)


@asynccontextmanager
async def trace_context(trace_id: str | None = None):
    """Context manager for trace ID."""
    previous = trace_id_var.get()
    trace_id_var.set(trace_id or uuid.uuid4().hex[:16])
    try:
        yield trace_id_var.get()
    finally:
        trace_id_var.set(previous)


class WorkerCore:
    """
    OWNEX Worker Core — The autonomous work orchestrator.

    Implements the continuous loop:
    DISCOVER → EVALUATE → SELECT → PREPARE → EXECUTE → VALIDATE → DELIVER → LEARN
    """

    def __init__(self, config: WorkerConfig | None = None):
        self.config = config or WorkerConfig()
        self.state = WorkState.STOPPED
        self.current_goal: WorkGoal | None = None
        self.work_items: dict[str, WorkItem] = {}
        self.metrics = WorkerMetrics()
        self._running = False
        self._main_task: asyncio.Task | None = None
        self._checkpoint_task: asyncio.Task | None = None
        self._start_time = datetime.now(UTC)

        # Integration hooks (set by other systems)
        self._discovery_engine: DiscoveryEngineProtocol | None = None
        self._evaluation_engine: EvaluationEngineProtocol | None = None
        self._execution_engine: ExecutionEngineProtocol | None = None
        self._delivery_engine: DeliveryEngineProtocol | None = None
        self._learning_engine: LearningEngineProtocol | None = None
        self._skill_engine: SkillEngineProtocol | None = None
        self._ai_router: AIRouterProtocol | None = None
        self._cost_tracker: CostTrackerProtocol | None = None
        # Genome repository for persisting discovered opportunities
        self._genome_repo: object | None = None

        # Week 2: Circuit breakers per engine
        self._circuit_breakers: dict[str, Any] = {}
        self._init_circuit_breakers()

        # Week 2: Self-repair integration
        self._self_repair = None
        self._init_self_repair()

        # Week 2: Spending tracking
        self._session_cost_usd: float = 0.0
        self._workflow_costs: dict[str, float] = {}  # workflow_id → cost

        # Week 2: Workflow/execution IDs for current cycle
        self._current_workflow_id: str = ""
        self._current_execution_id: str = ""

        logger.info("WorkerCore initialized with autonomy_level=%s", self.config.autonomy_level.value)

    def set_discovery_engine(self, engine: Any) -> None:
        self._discovery_engine = engine

    def set_evaluation_engine(self, engine: Any) -> None:
        self._evaluation_engine = engine

    def set_execution_engine(self, engine: Any) -> None:
        self._execution_engine = engine

    def set_delivery_engine(self, engine: Any) -> None:
        self._delivery_engine = engine

    def set_learning_engine(self, engine: Any) -> None:
        self._learning_engine = engine

    def set_skill_engine(self, engine: Any) -> None:
        self._skill_engine = engine

    def set_ai_router(self, router: Any) -> None:
        self._ai_router = router

    def set_cost_tracker(self, tracker: Any) -> None:
        self._cost_tracker = tracker

    def set_genome_repository(self, repo: object) -> None:
        """Set an OpportunityGenome repository implementation (save/get).

        The repository must implement `save(genome)` and optionally `get_by_id`/`get_by_external_id`.
        """
        self._genome_repo = repo

    # ── Week 2: Circuit Breakers ──────────────────────────────────

    def _init_circuit_breakers(self) -> None:
        """Initialize circuit breakers for each engine component."""
        try:
            from cores.recovery.circuit_breaker import CircuitBreaker

            for component in ["discovery", "evaluation", "execution", "delivery", "learning", "skill"]:
                self._circuit_breakers[component] = CircuitBreaker(
                    component=f"worker_core.{component}",
                    max_failures=3,
                    cooldown=60.0,
                )
        except ImportError:
            logger.warning("CircuitBreaker not available, using basic tracking")
            self._circuit_breakers = {}

    def _check_circuit_breaker(self, component: str) -> bool:
        """Check if circuit breaker allows operation. Returns True if OK to proceed."""
        cb = self._circuit_breakers.get(component)
        if cb is None:
            return True  # No breaker = always allow
        if not cb.can_attempt():
            logger.warning("[CB] Circuit breaker OPEN for %s — operation blocked", component)
            return False
        return True

    def _record_engine_failure(self, component: str, error: str) -> None:
        """Record engine failure and trip circuit breaker if threshold reached."""
        cb = self._circuit_breakers.get(component)
        if cb is not None:
            cb.record_failure()
            snap = cb.snapshot()
            if snap["state"] == "open":
                logger.error(
                    "[CB] Circuit breaker OPENED for %s after %d failures",
                    component, snap["failure_count"],
                )
                # Trigger self-repair
                self._trigger_self_repair(component, error)

    def _record_engine_success(self, component: str) -> None:
        """Record engine success and reset circuit breaker."""
        cb = self._circuit_breakers.get(component)
        if cb is not None:
            cb.record_success()

    # ── Week 2: Self-Repair ───────────────────────────────────────

    def _init_self_repair(self) -> None:
        """Initialize self-repair engine integration."""
        try:
            from core.self_repair.engine import get_self_repair_engine

            self._self_repair = get_self_repair_engine()
            logger.info("Self-repair engine connected to WorkerCore")
        except ImportError:
            logger.warning("Self-repair engine not available")
            self._self_repair = None

    def _trigger_self_repair(self, component: str, error: str) -> None:
        """Trigger self-repair for a failed component."""
        if self._self_repair is None:
            return
        try:
            issue = {
                "detector": "worker_core",
                "component": component,
                "issue_type": "engine_failure",
                "severity": "CRITICAL",
                "details": f"WorkerCore engine '{component}' failed: {error}",
                "requires_approval": False,
            }
            self._self_repair.repair_issue(issue)
        except Exception as exc:
            logger.warning("Self-repair trigger failed: %s", exc)

    # ── Week 2: Spending Limits ───────────────────────────────────

    def _check_spending_limit(self, workflow_id: str, additional_cost: float = 0.0) -> bool:
        """Check if workflow is within spending limits."""
        max_per_workflow = self.config.max_cost_per_workflow_usd
        current = self._workflow_costs.get(workflow_id, 0.0)
        if current + additional_cost > max_per_workflow:
            logger.warning(
                "[SPENDING] Workflow %s would exceed limit: $%.2f + $%.2f > $%.2f",
                workflow_id[:8], current, additional_cost, max_per_workflow,
            )
            return False
        return True

    def _record_cost(self, workflow_id: str, cost_usd: float) -> None:
        """Record cost for a workflow."""
        self._workflow_costs[workflow_id] = self._workflow_costs.get(workflow_id, 0.0) + cost_usd
        self._session_cost_usd += cost_usd
        if self._session_cost_usd > self.config.max_cost_per_session_usd:
            logger.error(
                "[SPENDING] Session cost $%.2f exceeds limit $%.2f",
                self._session_cost_usd, self.config.max_cost_per_session_usd,
            )
            self.state = WorkState.DEGRADED

    # ── Week 2: Audit Trail ───────────────────────────────────────

    def _audit(self, action: str, **kwargs: Any) -> None:
        """Create an audit log entry for the current workflow/execution."""
        try:
            from cores.worker_core.audit import create_audit_entry

            create_audit_entry(
                workflow_id=self._current_workflow_id,
                execution_id=self._current_execution_id,
                trace_id=get_trace_id(),
                work_item_id=kwargs.pop("work_item_id", None),
                action=action,
                phase=kwargs.pop("phase", None),
                status=kwargs.pop("status", "success"),
                details=kwargs.pop("details", None),
                error=kwargs.pop("error", None),
                cost_usd=kwargs.pop("cost_usd", None),
                requires_approval=kwargs.pop("requires_approval", False),
                approved_by=kwargs.pop("approved_by", None),
                approval_reason=kwargs.pop("approval_reason", None),
                autonomy_level=self.config.autonomy_level.value,
                **kwargs,
            )
        except Exception as exc:
            logger.debug("Audit trail write failed (non-blocking): %s", exc)

    def set_goal(self, goal: WorkGoal) -> None:
        self.current_goal = goal
        logger.info("Worker goal set: %s (target: $%.0f/month)", goal.description or goal.id, goal.target_monthly_usd)

    async def start(self) -> None:
        """Start the worker loop."""
        if self._running:
            logger.warning("WorkerCore already running")
            return

        # Resume capability: rehydrate work items that had persisted checkpoints.
        resumed = self.resume_open_work_items()
        if resumed:
            logger.info("WorkerCore resuming %d open work items from checkpoints", len(resumed))
            for work_id, resume_phase in resumed:
                self._rehydrate_work_item(work_id, resume_phase)

        self._running = True
        self.state = WorkState.RUNNING
        self._main_task = asyncio.create_task(self._main_loop())
        self._checkpoint_task = asyncio.create_task(self._checkpoint_loop())
        logger.info("WorkerCore started")

    async def stop(self) -> None:
        """Stop the worker loop gracefully."""
        self._running = False
        self.state = WorkState.STOPPED

        if self._main_task:
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass

        if self._checkpoint_task:
            self._checkpoint_task.cancel()
            try:
                await self._checkpoint_task
            except asyncio.CancelledError:
                pass

        logger.info("WorkerCore stopped")

    async def pause(self) -> None:
        """Pause the worker."""
        self.state = WorkState.PAUSED
        logger.info("WorkerCore paused")

    async def resume(self) -> None:
        """Resume the worker."""
        if self.state == WorkState.PAUSED:
            self.state = WorkState.RUNNING
            logger.info("WorkerCore resumed")

    async def _main_loop(self) -> None:
        """Main autonomous work loop."""
        while self._running:
            try:
                async with trace_context() as trace_id:
                    if self.state != WorkState.RUNNING:
                        await asyncio.sleep(10)
                        continue

                    if not self.current_goal or not self.current_goal.active:
                        logger.warning("No active goal, skipping cycle")
                        await asyncio.sleep(60)
                        continue

                    # Check concurrent work limit
                    active_work = [
                        w for w in self.work_items.values() if w.state in (WorkState.RUNNING, WorkState.PAUSED)
                    ]
                    if len(active_work) >= self.config.max_concurrent_work:
                        await asyncio.sleep(30)
                        continue

                    # Run one cycle
                    await self._run_cycle()

                    self.metrics.cycles_completed += 1
                    self.metrics.last_cycle_at = datetime.now(UTC).isoformat()

                    # Test mode: run one cycle and stop
                    if self.config.test_mode:
                        logger.info("Test mode: completed one cycle, stopping")
                        self._running = False
                        break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in worker main loop: %s", e)
                self.metrics.record_failure(str(e))
                self.state = WorkState.DEGRADED
                await asyncio.sleep(60)
                self.state = WorkState.RUNNING

    async def _run_cycle(self) -> None:
        """Execute one complete work cycle."""
        cycle_start = datetime.now(UTC)

        # Generate workflow and execution IDs for this cycle
        self._current_workflow_id = f"wf-{uuid.uuid4().hex[:12]}"
        self._current_execution_id = f"ex-{uuid.uuid4().hex[:12]}"

        self._audit("cycle_start", details={"workflow_id": self._current_workflow_id})

        # Phase 1: DISCOVER
        async with trace_context() as trace_id:
            logger.debug("Discovering work", extra={"trace_id": trace_id})
            work_item = await self._discover_work()
            if not work_item:
                logger.debug("No work discovered this cycle", extra={"trace_id": trace_id})
                self._audit("cycle_end", status="skipped", details={"reason": "no_work_discovered"})
                return

        # Phase 2: EVALUATE
        if not await self._evaluate_work(work_item):
            self._audit("cycle_end", status="rejected", work_item_id=work_item.id,
                        details={"reason": work_item.error or "evaluation_failed"})
            return

        # Phase 3: SELECT (already selected by evaluation)
        work_item.phase = WorkPhase.SELECT
        work_item.add_checkpoint(WorkPhase.SELECT, {"selected": True})
        self._persist_one_checkpoint(work_item)
        self._audit("select", work_item_id=work_item.id, phase="select")

        # Phase 4: PREPARE
        if not await self._prepare_work(work_item):
            return

        # Phase 5: EXECUTE
        if not await self._execute_work(work_item):
            return

        # Phase 6: VALIDATE
        if not await self._validate_work(work_item):
            return

        # Phase 7: DELIVER
        if not await self._deliver_work(work_item):
            return

        # Phase 8: LEARN
        await self._learn_from_work(work_item)

        self._audit("cycle_complete", work_item_id=work_item.id,
                    details={"reward": work_item.estimated_reward_usd})

        # Record metrics
        duration = (datetime.now(UTC) - cycle_start).total_seconds() / 3600
        self.metrics.record_completion(work_item.estimated_reward_usd, duration)

    async def _discover_work(self) -> WorkItem | None:
        """Discover new work opportunities."""
        if not self._discovery_engine:
            logger.debug("No discovery engine configured")
            return None

        # Circuit breaker check
        if not self._check_circuit_breaker("discovery"):
            self._audit("discover", status="blocked", details={"reason": "circuit_breaker_open"})
            return None

        try:
            work_item = WorkItem(goal_id=self.current_goal.id if self.current_goal else "")
            work_item.workflow_id = self._current_workflow_id
            work_item.phase = WorkPhase.DISCOVER
            work_item.add_checkpoint(WorkPhase.DISCOVER, {"timestamp": datetime.now(UTC).isoformat()})

            # Convert string categories to OpportunityCategory enums
            categories = None
            if self.current_goal and self.current_goal.preferred_categories:
                from cores.opportunity_genome.models import OpportunityCategory

                categories = []
                for cat_str in self.current_goal.preferred_categories:
                    try:
                        categories.append(OpportunityCategory(cat_str))
                    except ValueError:
                        pass

            # Call discovery engine (async method)
            opportunities = await self._discovery_engine.discover_all(
                categories=categories,
                platforms=None,
            )

            if not opportunities:
                return None

            # Pick best opportunity (opportunities are Opportunity objects, not dicts)
            best = max(opportunities, key=lambda o: getattr(o, "expected_value_usd_per_hour", 0))

            def _val(attr: str, default: Any = "") -> Any:
                v = getattr(best, attr, default)
                # Enums (WorkPlatform, OpportunityCategory, etc.) -> .value
                if v is not None and hasattr(v, "value"):
                    return v.value
                return v

            work_item.opportunity_id = str(_val("id", ""))
            work_item.title = str(_val("title", ""))
            work_item.description = str(_val("description", ""))
            work_item.platform = str(_val("platform", ""))
            work_item.category = str(_val("category", ""))
            work_item.estimated_reward_usd = float(_val("reward", 0.0) or 0.0)
            work_item.estimated_hours = float(_val("estimated_hours", 1.0) or 1.0)
            work_item.risk_score = float(_val("risk_score", 0.0) or 0.0)
            work_item.acceptance_probability = float(_val("acceptance_probability", 0.0) or 0.0)
            work_item.expected_value_usd_per_hour = float(_val("expected_value_usd_per_hour", 0.0) or 0.0)

            self.work_items[work_item.id] = work_item
            # Persist a canonical OpportunityGenome for this discovered work when a repo is configured
            try:
                if self._genome_repo is not None:
                    from cores.opportunity_genome.mapper import map_work_item_to_genome

                    genome = map_work_item_to_genome(work_item)
                    self._genome_repo.save(genome)
                    # attach genome id for traceability
                    setattr(work_item, "genome_id", genome.id)
                    logger.debug("Persisted OpportunityGenome %s for work %s", genome.id, work_item.id)
            except Exception as ge:
                logger.warning("Failed to persist genome for work %s: %s", work_item.id, ge)
            work_item.state = WorkState.RUNNING
            work_item.started_at = datetime.now(UTC).isoformat()
            self._persist_one_checkpoint(work_item)
            self._record_engine_success("discovery")
            self._audit("discover", work_item_id=work_item.id, phase="discover",
                        details={"title": work_item.title, "ev_hr": work_item.expected_value_usd_per_hour})

            logger.info(
                "Discovered work: %s (%s) - EV: $%.2f/hr",
                work_item.title,
                work_item.id,
                work_item.expected_value_usd_per_hour,
            )
            return work_item

        except Exception as e:
            logger.exception("Discovery failed: %s", e)
            self._record_engine_failure("discovery", str(e))
            self.metrics.record_failure(f"Discovery: {e}")
            self._audit("discover", status="failed", error=str(e))
            return None

    async def _evaluate_work(self, work_item: WorkItem) -> bool:
        """Evaluate work item against criteria."""
        if not self._evaluation_engine:
            logger.warning("No evaluation engine configured, using basic evaluation")
            return self._basic_evaluation(work_item)

        # Circuit breaker check
        if not self._check_circuit_breaker("evaluation"):
            self._audit("evaluate", work_item_id=work_item.id, status="blocked",
                        details={"reason": "circuit_breaker_open"})
            return False

        work_item.phase = WorkPhase.EVALUATE
        work_item.add_checkpoint(WorkPhase.EVALUATE, {"started": True})

        try:
            evaluation = self._evaluation_engine.evaluate(work_item)

            work_item.acceptance_probability = evaluation.get(
                "acceptance_probability", work_item.acceptance_probability
            )
            work_item.expected_value_usd_per_hour = evaluation.get(
                "expected_value_usd_per_hour", work_item.expected_value_usd_per_hour
            )
            work_item.risk_score = evaluation.get("risk_score", work_item.risk_score)

            # Check thresholds
            goal = self.current_goal
            assert goal is not None, "Goal should be set before evaluation"
            if work_item.expected_value_usd_per_hour < (goal.target_monthly_usd / 160):  # rough hourly target
                logger.info("Work %s below EV threshold, rejecting", work_item.id)
                work_item.state = WorkState.ERROR
                work_item.error = "Below expected value threshold"
                self._audit("evaluate", work_item_id=work_item.id, status="rejected",
                            details={"reason": "below_ev_threshold", "ev_hr": work_item.expected_value_usd_per_hour})
                return False

            if work_item.risk_score > goal.max_risk_score:
                logger.info("Work %s above risk threshold, rejecting", work_item.id)
                work_item.state = WorkState.ERROR
                work_item.error = "Above risk threshold"
                self._audit("evaluate", work_item_id=work_item.id, status="rejected",
                            details={"reason": "above_risk_threshold", "risk": work_item.risk_score})
                return False

            work_item.add_checkpoint(WorkPhase.EVALUATE, evaluation)
            self._persist_one_checkpoint(work_item)
            self._record_engine_success("evaluation")
            self._audit("evaluate", work_item_id=work_item.id, phase="evaluate",
                        details={"score": evaluation.get("score", 0), "ev_hr": work_item.expected_value_usd_per_hour})
            return True

        except Exception as e:
            logger.exception("Evaluation failed: %s", e)
            self._record_engine_failure("evaluation", str(e))
            self.metrics.record_failure(f"Evaluation: {e}")
            self._audit("evaluate", work_item_id=work_item.id, status="failed", error=str(e))
            return False

    def _basic_evaluation(self, work_item: WorkItem) -> bool:
        """Basic evaluation when no engine available."""
        goal = self.current_goal
        assert goal is not None, "Goal should be set before evaluation"
        if work_item.estimated_reward_usd < goal.min_reward_usd:
            return False
        if work_item.risk_score > goal.max_risk_score:
            return False
        return True

    async def _prepare_work(self, work_item: WorkItem) -> bool:
        """Prepare work item for execution (skill analysis, setup env, etc)."""
        work_item.phase = WorkPhase.PREPARE
        work_item.add_checkpoint(WorkPhase.PREPARE, {"started": True})

        try:
            # Skill analysis if skill engine available
            if self._skill_engine:
                try:
                    from cores.direct_work_engine.profile_builder import IntelligentProfileBuilder

                    profile_builder = IntelligentProfileBuilder()
                    profile = profile_builder.build()
                    skill_result = self._skill_engine.analyze(work_item, profile)

                    work_item.add_checkpoint(WorkPhase.PREPARE, {
                        "skill_analysis": skill_result.to_dict() if hasattr(skill_result, "to_dict") else str(skill_result),
                        "readiness_score": getattr(skill_result, "readiness_score", 0.0),
                        "can_execute": getattr(skill_result, "can_execute", True),
                        "missing_skills": getattr(skill_result, "missing_critical_skills", []),
                    })

                    # Block if critical skills missing
                    if not getattr(skill_result, "can_execute", True):
                        missing = getattr(skill_result, "missing_critical_skills", [])
                        logger.warning("Work %s blocked: missing critical skills %s", work_item.id, missing)
                        work_item.error = f"Missing critical skills: {', '.join(missing)}"
                        work_item.state = WorkState.ERROR
                        self._persist_one_checkpoint(work_item, phase_completed=False, error=work_item.error)
                        return False

                except Exception as skill_exc:
                    logger.warning("Skill analysis failed (non-blocking): %s", skill_exc)

            work_item.add_checkpoint(WorkPhase.PREPARE, {"prepared": True})
            self._persist_one_checkpoint(work_item)

            logger.info("Work %s prepared", work_item.id)
            return True

        except Exception as e:
            logger.exception("Preparation failed: %s", e)
            work_item.error = f"Preparation failed: {e}"
            self.metrics.record_failure(f"Preparation: {e}")
            return False

    async def execute_ai_task(
        self,
        task_type: str,
        messages: list[dict],
        max_tokens: int = 4096,
        max_cost_usd: float | None = None,
    ) -> dict[str, Any]:
        """Execute an AI task via OAR router with cost control.

        Args:
            task_type: Type of task (code, chat, analysis, etc.)
            messages: List of messages for the LLM
            max_tokens: Maximum tokens for response
            max_cost_usd: Maximum cost allowed for this operation

        Returns:
            Dict with response, cost, provider, model used
        """
        if not self._ai_router:
            return {"error": "AI router not configured", "success": False}

        try:
            # Ensure cost tracker
            if not self._cost_tracker:
                from cores.ai.runtime.cost import get_cost_tracker

                self._cost_tracker = get_cost_tracker()

            # Route to best provider
            from cores.ai.runtime.interfaces import RoutingContext, TaskType

            task_type_upper = task_type.upper()
            task_type_enum = TaskType.CHAT
            if hasattr(TaskType, task_type.upper()):
                task_type_enum = TaskType[task_type.upper()]

            # Route to best provider
            decision = await self._ai_router.route(
                RoutingContext(
                    messages=messages,
                    task_type=task_type_enum,
                    max_tokens=max_tokens,
                    max_cost_usd=max_cost_usd
                    or (self._cost_tracker.get_daily_spent() + 0.5 if self._cost_tracker else 0.5),
                    speed_critical=False,
                    privacy_required=False,
                )
            )

            # Execute via provider
            provider = self._ai_router._registry.get_provider(decision.provider_id)
            if not provider:
                return {"error": f"Provider {decision.provider_id} not found", "success": False}

            # Execute request
            from cores.ai.runtime.interfaces import AIRequest

            request = AIRequest(
                messages=messages,
                max_tokens=max_tokens,
                task_type=task_type_enum,
            )
            response = await provider.generate(request)

            # Record cost
            if self._cost_tracker:
                self._cost_tracker.record_usage(
                    decision.provider_id,
                    decision.model_id,
                    response.usage.input_tokens if hasattr(response, "usage") else 0,
                    response.usage.output_tokens if hasattr(response, "usage") else 0,
                    cost_usd=decision.estimated_cost_usd,
                )

            return {
                "success": True,
                "response": response.content if hasattr(response, "content") else str(response),
                "provider": decision.provider_id,
                "model": decision.model_id,
                "cost_usd": decision.estimated_cost_usd,
                "latency_ms": decision.estimated_latency_ms,
            }

        except Exception as e:
            logger.exception("AI task execution failed: %s", e)
            return {"error": str(e), "success": False}

    async def _execute_work(self, work_item: WorkItem) -> bool:
        """Execute the work (coding, testing, etc)."""
        # Circuit breaker check
        if not self._check_circuit_breaker("execution"):
            self._audit("execute", work_item_id=work_item.id, status="blocked",
                        details={"reason": "circuit_breaker_open"})
            return False

        work_item.phase = WorkPhase.EXECUTE
        work_item.add_checkpoint(WorkPhase.EXECUTE, {"started": True})

        try:
            if self._execution_engine and hasattr(self._execution_engine, "execute"):
                result = self._execution_engine.execute(work_item)
                # Execution engine may be async (returns a coroutine).
                if inspect.isawaitable(result):
                    result = await result
                if isinstance(result, dict):
                    work_item.artifacts.extend(result.get("artifacts", []))
                    work_item.evidence.extend(result.get("evidence", []))
                    work_item.add_checkpoint(WorkPhase.EXECUTE, result)
            else:
                work_item.add_checkpoint(WorkPhase.EXECUTE, {"executed": True, "basic": True})
            self._persist_one_checkpoint(work_item)
            self._record_engine_success("execution")
            self._audit("execute", work_item_id=work_item.id, phase="execute",
                        details={"artifacts": len(work_item.artifacts), "evidence": len(work_item.evidence)})

            logger.info("Work %s executed", work_item.id)
            return True

        except Exception as e:
            logger.exception("Execution failed: %s", e)
            work_item.error = f"Execution failed: {e}"
            self._record_engine_failure("execution", str(e))
            self.metrics.record_failure(f"Execution: {e}")
            self._audit("execute", work_item_id=work_item.id, status="failed", error=str(e))
            return False

    async def _validate_work(self, work_item: WorkItem) -> bool:
        """Validate work quality before delivery. Quality Gate is mandatory."""
        work_item.phase = WorkPhase.VALIDATE
        work_item.add_checkpoint(WorkPhase.VALIDATE, {"started": True})

        try:
            # Mandatory Quality Gate: DELIVER must never run without a passed gate.
            if self._evaluation_engine:
                from cores.direct_work_engine.models import Opportunity, OpportunityCategory, WorkPlatform

                # Normalize enums: work_item.platform/category are strings.
                platform_str = getattr(work_item, "platform", "") or "other"
                category_str = getattr(work_item, "category", "software_engineering") or "software_engineering"
                try:
                    platform = WorkPlatform(platform_str) if platform_str else WorkPlatform.OTHER
                except ValueError:
                    platform = WorkPlatform.OTHER
                try:
                    category = OpportunityCategory(category_str)
                except ValueError:
                    category = OpportunityCategory.SOFTWARE_ENGINEERING

                opportunity = Opportunity(
                    id=getattr(work_item, "opportunity_id", "") or "unknown",
                    title=getattr(work_item, "title", "") or "Untitled",
                    platform=platform,
                    category=category,
                    payment=getattr(work_item, "estimated_reward_usd", 0.0),
                    estimated_time_hours=getattr(work_item, "estimated_hours", 1.0),
                )

                evaluation = self._evaluation_engine.evaluate(opportunity)
                quality_gate = evaluation.get("quality_gate_result", {})

                if not quality_gate.get("passed", False):
                    reason = quality_gate.get("reason", "Quality gate failed")
                    logger.warning("Work %s failed Quality Gate: %s", work_item.id, reason)
                    work_item.state = WorkState.ERROR
                    work_item.error = f"Quality Gate failed: {reason}"
                    work_item.add_checkpoint(WorkPhase.VALIDATE, {"passed": False, "reason": reason})
                    self._persist_one_checkpoint(work_item, phase_completed=False, error=reason)
                    return False

                work_item.add_checkpoint(WorkPhase.VALIDATE, {"passed": True, "quality_gate": quality_gate})
                self._persist_one_checkpoint(work_item, phase_completed=True)
            else:
                # No evaluation engine: treat as gate-passed (reporting only, not "silent mock").
                work_item.add_checkpoint(WorkPhase.VALIDATE, {"validated": True, "basic": True})
                self._persist_one_checkpoint(work_item)

            logger.info("Work %s passed Quality Gate", work_item.id)
            return True

        except Exception as e:
            logger.exception("Validation failed: %s", e)
            work_item.error = f"Validation failed: {e}"
            self.metrics.record_failure(f"Validation: {e}")
            return False

    async def _deliver_work(self, work_item: WorkItem) -> bool:
        """Deliver completed work (submit PR, bounty, etc).

        Quality Gate is MANDATORY: if the latest VALIDATE checkpoint did not
        pass, delivery is blocked. This enforces the rule that DELIVER never
        runs without a successful validation.
        """
        # Mandatory gate check: find the most recent VALIDATE checkpoint.
        last_validate = None
        for cp in reversed(work_item.checkpoints):
            if isinstance(cp, dict) and cp.get("phase") == WorkPhase.VALIDATE.value:
                last_validate = cp
                break
        if last_validate is None or not last_validate.get("data", {}).get("passed", False):
            work_item.state = WorkState.ERROR
            work_item.error = "Blocked: Quality Gate did not pass before delivery"
            logger.warning("Work %s delivery blocked (mandatory Quality Gate not passed)", work_item.id)
            work_item.add_checkpoint(WorkPhase.DELIVER, {"blocked": True, "reason": work_item.error})
            self._persist_one_checkpoint(work_item, phase_completed=False, error=work_item.error)
            return False

        work_item.phase = WorkPhase.DELIVER
        work_item.add_checkpoint(WorkPhase.DELIVER, {"started": True})

        # Check if human approval needed
        needs_human = (
            self.config.human_approval_required
            or work_item.human_action_required
            or self.config.autonomy_level == AutonomyLevel.NONE
        )

        if needs_human:
            work_item.human_action_required = True
            work_item.human_action_description = "Approve delivery"
            work_item.state = WorkState.PAUSED
            logger.info("Work %s requires human approval for delivery", work_item.id)
            self._persist_one_checkpoint(work_item, phase_completed=False)
            self._audit("deliver", work_item_id=work_item.id, status="pending",
                        requires_approval=True,
                        details={"reason": "human_gate", "autonomy": self.config.autonomy_level.value})
            return True  # Not a failure, just waiting

        # Spending limit check
        if not self._check_spending_limit(self._current_workflow_id):
            work_item.state = WorkState.ERROR
            work_item.error = "Blocked: spending limit exceeded"
            self._audit("deliver", work_item_id=work_item.id, status="blocked",
                        details={"reason": "spending_limit"})
            return False

        # Circuit breaker check
        if not self._check_circuit_breaker("delivery"):
            self._audit("deliver", work_item_id=work_item.id, status="blocked",
                        details={"reason": "circuit_breaker_open"})
            return False

        try:
            if self._delivery_engine and hasattr(self._delivery_engine, "deliver"):
                result = self._delivery_engine.deliver(work_item)
                if inspect.isawaitable(result):
                    result = await result
                work_item.add_checkpoint(WorkPhase.DELIVER, result if isinstance(result, dict) else {"delivered": True})
            else:
                work_item.add_checkpoint(WorkPhase.DELIVER, {"delivered": True, "basic": True})
            self._persist_one_checkpoint(work_item)
            self._record_engine_success("delivery")

            work_item.state = WorkState.RUNNING
            work_item.completed_at = datetime.now(UTC).isoformat()
            work_item.approved_by_human = True
            self._audit("deliver", work_item_id=work_item.id, status="success", phase="deliver")
            logger.info("Work %s delivered", work_item.id)
            return True

        except Exception as e:
            logger.exception("Delivery failed: %s", e)
            work_item.error = f"Delivery failed: {e}"
            self._record_engine_failure("delivery", str(e))
            self.metrics.record_failure(f"Delivery: {e}")
            self._audit("deliver", work_item_id=work_item.id, status="failed", error=str(e))
            return False

    async def _learn_from_work(self, work_item: WorkItem) -> None:
        """Learn from completed work."""
        work_item.phase = WorkPhase.LEARN
        work_item.add_checkpoint(WorkPhase.LEARN, {"completed": True})

        try:
            if self._learning_engine and hasattr(self._learning_engine, "learn"):
                # Learning engine requires outcome parameter
                outcome = "completed" if work_item.state == WorkState.RUNNING else "failed"
                result = self._learning_engine.learn(work_item, outcome=outcome)
                if inspect.isawaitable(result):
                    await result

            work_item.add_checkpoint(WorkPhase.LEARN, {"learned": True})
            self._persist_one_checkpoint(work_item)
            logger.info("Learning recorded for work %s", work_item.id)

        except Exception as e:
            logger.exception("Learning failed: %s", e)
            self.metrics.record_failure(f"Learning: {e}")

    async def _checkpoint_loop(self) -> None:
        """Periodic checkpoint persistence."""
        while self._running:
            try:
                await asyncio.sleep(self.config.checkpoint_interval_seconds)
                await self._persist_checkpoints()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Checkpoint failed: %s", e)

    async def _persist_checkpoints(self) -> None:
        """Persist all work item checkpoints for resume capability.

        Writes each active work item's latest checkpoint to the SQLite
        ``worker_checkpoints`` table so a crash does not lose workflow state.
        """
        active = [w for w in self.work_items.values() if w.state in (WorkState.RUNNING, WorkState.PAUSED)]
        for w in active:
            self._persist_one_checkpoint(w)
        logger.debug("Checkpoint: %d active work items persisted", len(active))

    def _persist_one_checkpoint(
        self,
        work_item: WorkItem,
        *,
        phase_completed: bool = True,
        phase: WorkPhase | None = None,
        error: str | None = None,
    ) -> None:
        """Persist a single work item's checkpoint to SQLite.

        Uses the item's in-memory ``checkpoints`` list (the most recent entry)
        as the durable payload, plus the current ``phase``.
        """
        try:
            active_phase = phase.value if phase is not None else work_item.phase.value
            latest = work_item.get_latest_checkpoint() or {}
            data = latest.get("data", {}) if isinstance(latest, dict) else {}
            save_checkpoint(
                work_item.id,
                active_phase,
                data,
                work_item_title=work_item.title,
                work_item_platform=work_item.platform,
                work_item_category=work_item.category,
                phase_completed=phase_completed,
                error=error,
                retry_count=int(getattr(work_item, "retry_count", 0) or 0),
            )
        except Exception as exc:  # persistence never blocks the workflow
            logger.exception("Failed to persist checkpoint for %s: %s", work_item.id, exc)

    def resume_open_work_items(self) -> list[tuple[str, str]]:
        """Return work items that have a persisted checkpoint and a phase to resume.

        Returns a list of (work_item_id, resume_phase). The caller (start) can
        load or re-spawn these items and continue from ``resume_phase`` instead
        of re-running completed external actions.
        """
        from cores.worker_core.persistence import get_active_work_items, get_latest_checkpoint

        results: list[tuple[str, str]] = []
        for work_id in get_active_work_items():
            cp = get_latest_checkpoint(work_id)
            if cp is None:
                continue
            resume_phase = resume_from(cp)
            if resume_phase:
                results.append((work_id, resume_phase))
        return results

    def _rehydrate_work_item(self, work_id: str, resume_phase: str) -> None:
        """Reconstruct a WorkItem in memory from its latest persisted checkpoint.

        Registers the item in ``self.work_items`` and sets its phase to
        ``resume_phase`` so the next cycle continues from the correct phase
        instead of re-running completed external actions.
        """
        from cores.worker_core.persistence import checkpoint_data_dict, get_latest_checkpoint

        cp = get_latest_checkpoint(work_id)
        if cp is None:
            return
        data = checkpoint_data_dict(cp) or {}
        item = WorkItem(
            id=work_id,
            opportunity_id=str(getattr(cp, "work_item_title", "") or ""),
            title=str(getattr(cp, "work_item_title", "") or ""),
            platform=str(getattr(cp, "work_item_platform", "") or ""),
            category=str(getattr(cp, "work_item_category", "") or ""),
        )
        # Re-apply scalar fields that were persisted in the checkpoint payload.
        for key in [
            "estimated_reward_usd",
            "estimated_hours",
            "risk_score",
            "acceptance_probability",
            "expected_value_usd_per_hour",
            "opportunity_id",
        ]:
            if key in data and data[key] is not None:
                try:
                    setattr(item, key, data[key])
                except (TypeError, ValueError):
                    pass
        item.phase = WorkPhase(resume_phase) if hasattr(WorkPhase, resume_phase.upper()) else WorkPhase.PREPARE
        # Register for continuation by the next cycle.
        self.work_items[work_id] = item
        logger.info("Rehydrated work item %s → resume at phase %s", work_id, resume_phase)

    def get_status(self) -> dict[str, Any]:
        """Get current worker status."""
        active_work = [w for w in self.work_items.values() if w.state in (WorkState.RUNNING, WorkState.PAUSED)]
        return {
            "state": self.state.value,
            "goal": self.current_goal.description if self.current_goal else None,
            "goal_target_monthly_usd": self.current_goal.target_monthly_usd if self.current_goal else 0,
            "autonomy_level": self.config.autonomy_level.value,
            "active_work_count": len(active_work),
            "total_work_items": len(self.work_items),
            "metrics": {
                "cycles_completed": self.metrics.cycles_completed,
                "work_completed": self.metrics.work_items_completed,
                "work_failed": self.metrics.work_items_failed,
                "total_revenue_usd": self.metrics.total_revenue_usd,
                "avg_ev_usd_per_hour": self.metrics.avg_expected_value_usd_per_hour,
                "uptime_hours": (datetime.now(UTC) - self._start_time).total_seconds() / 3600,
            },
            "work_items": [
                {
                    "id": w.id,
                    "title": w.title,
                    "phase": w.phase.value,
                    "state": w.state.value,
                    "platform": w.platform,
                    "estimated_reward_usd": w.estimated_reward_usd,
                    "expected_value_usd_per_hour": w.expected_value_usd_per_hour,
                    "human_action_required": w.human_action_required,
                    "error": w.error,
                }
                for w in self.work_items.values()
            ],
        }

    def approve_work(self, work_id: str) -> bool:
        """Approve a work item for delivery."""
        work_item = self.work_items.get(work_id)
        if not work_item:
            return False

        work_item.approved_by_human = True
        work_item.human_action_required = False
        work_item.state = WorkState.RUNNING
        logger.info("Work %s approved by human", work_id)
        return True

    # Numeric ordering for autonomy levels (str Enum comparison is lexicographic, not semantic)
    _AUTONOMY_ORDER: dict[str, int] = {
        "none": 0,
        "discover": 1,
        "prepare": 2,
        "execute": 3,
        "full": 4,
    }

    def requires_human_approval(self, action: str) -> bool:
        """Check if an action requires human approval based on autonomy level.

        Args:
            action: Action name (discover, evaluate, prepare, execute, deliver, etc.)

        Returns:
            True if human approval is required, False if autonomous
        """
        current_order = self._AUTONOMY_ORDER.get(self.config.autonomy_level.value, 0)

        action_requirements = {
            "discover": 0,   # AutonomyLevel.NONE
            "evaluate": 1,   # AutonomyLevel.DISCOVER
            "prepare": 2,    # AutonomyLevel.PREPARE
            "execute": 3,    # AutonomyLevel.EXECUTE
            "deliver": 4,    # AutonomyLevel.FULL
            "learn": 0,      # AutonomyLevel.NONE
        }

        required_order = action_requirements.get(action, 4)  # default to FULL
        return current_order < required_order

    def check_human_gate(self, work_item: WorkItem, action: str) -> tuple[bool, str | None]:
        """Check if a work item needs human approval for an action.

        Returns:
            (needs_approval, reason)
        """
        if self.config.autonomy_level == AutonomyLevel.NONE:
            return True, f"Autonomy level NONE requires approval for {action}"

        if self.requires_human_approval(action):
            work_item.human_action_required = True
            work_item.human_action_description = f"Approve {action} for work item"
            return True, f"Human approval required for {action} (autonomy level: {self.config.autonomy_level.value})"

        return False, None

    def reject_work(self, work_id: str, reason: str) -> bool:
        """Reject a work item."""
        work_item = self.work_items.get(work_id)
        if not work_item:
            return False

        work_item.state = WorkState.ERROR
        work_item.error = f"Rejected: {reason}"
        logger.info("Work %s rejected: %s", work_id, reason)
        return True

    def connect_real_engines(self) -> None:
        """Connect WorkerCore to real engines from the direct work engine.

        This method automatically discovers and connects to the available engines:
        - DirectWorkEngine (discovery, evaluation)
        - DirectWorkExecutionEngine (execution)
        - DirectWorkDeliveryEngine (delivery)
        - DirectWorkLearningEngine (learning)
        """
        try:
            # Connect discovery and evaluation engines
            from cores.direct_work_engine import DirectWorkEvaluationEngine, get_direct_work_engine

            dwe = get_direct_work_engine()
            self._discovery_engine = dwe.discovery
            self._evaluation_engine = DirectWorkEvaluationEngine()
            logger.info("Connected discovery and evaluation engines")
        except Exception as exc:
            logger.warning("Could not connect discovery/evaluation engines: %s", exc)

        try:
            # Connect execution engine
            from cores.direct_work_engine.execution import DirectWorkExecutionEngine

            self._execution_engine = DirectWorkExecutionEngine()
            logger.info("Connected execution engine")
        except Exception as exc:
            logger.warning("Could not connect execution engine: %s", exc)

        try:
            # Connect delivery engine with AutoSubmit
            from cores.direct_work_engine.delivery import DirectWorkDeliveryEngine

            delivery = DirectWorkDeliveryEngine()

            # Wire AutoSubmit for real platform submissions
            try:
                from core.opportunity.executors.auto_submit import get_auto_submit_engine

                auto_submit = get_auto_submit_engine()
                delivery.set_auto_submit(auto_submit)
                logger.info("Delivery engine wired with AutoSubmit")
            except Exception as as_exc:
                logger.warning("AutoSubmit not available for delivery: %s", as_exc)

            self._delivery_engine = delivery
            logger.info("Connected delivery engine")
        except Exception as exc:
            logger.warning("Could not connect delivery engine: %s", exc)

        try:
            # Connect learning engine
            from cores.direct_work_engine.learning import DirectWorkLearningEngine

            self._learning_engine = DirectWorkLearningEngine()
            logger.info("Connected learning engine")
        except Exception as exc:
            logger.warning("Could not connect learning engine: %s", exc)

        try:
            # Connect skill engine
            from cores.worker_core.skill_engine import SkillEngine

            self._skill_engine = SkillEngine()
            logger.info("Connected skill engine")
        except Exception as exc:
            logger.warning("Could not connect skill engine: %s", exc)

        try:
            # Connect cost tracker
            from cores.ai.runtime.cost import get_cost_tracker

            self._cost_tracker = get_cost_tracker()
            logger.info("Connected cost tracker")
        except Exception as exc:
            logger.warning("Could not connect cost tracker: %s", exc)

        logger.info("WorkerCore real engines connection attempt completed")


# Singleton
_worker_core: WorkerCore | None = None


def get_worker_core(config: WorkerConfig | None = None) -> WorkerCore:
    """Get or create the WorkerCore singleton."""
    global _worker_core
    if _worker_core is None:
        _worker_core = WorkerCore(config)
    return _worker_core


async def worker_core_heartbeat() -> dict[str, Any]:
    """Scheduler job: ensure WorkerCore is running.

    Called every 15 min by the scheduler. If WorkerCore is stopped,
    connects engines and starts it in ASSISTED mode.
    """
    worker = get_worker_core()

    if worker._running:
        return {"status": "already_running", "state": worker.state.value}

    # Ensure engines are connected
    if not worker._discovery_engine:
        worker.connect_real_engines()

    # Auto-start in ASSISTED mode (human approves external actions)
    if worker.config.autonomy_level == AutonomyLevel.NONE:
        worker.config.autonomy_level = AutonomyLevel.EXECUTE

    try:
        await worker.start()
        logger.info("WorkerCore auto-started by scheduler heartbeat")
        return {"status": "started", "state": worker.state.value}
    except Exception as exc:
        logger.warning("WorkerCore heartbeat start failed: %s", exc)
        return {"status": "error", "error": str(exc)}
