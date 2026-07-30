"""OWNEX Commander Agent — orchestrates the autonomous work platform.

The Commander is the top-level agent that coordinates all specialized agents
and system components to execute the OWNEX autonomous workflow.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from core.events.event_bus import get_core_event_bus
from cores.agents.base import BaseAgent
from cores.agents.types import AgentEvent, AgentId, EventType
from cores.discovery_engine import DiscoveryEngine, RankedOpportunity
from cores.platform_connectors.universal_connectors import PlatformConnectorManager
from cores.thinking_system import DailyPlan, ThinkingSystem

logger = logging.getLogger("ownex.commander")


class CommanderMode(Enum):
    """Commander operating modes."""

    OBSERVER = "observer"  # Only observes, no actions
    PREPARER = "preparer"  # Prepares plans, drafts, proposals
    SUPERVISOR = "supervisor"  # Executes with human approval
    AUTONOMOUS = "autonomous"  # Executes pre-approved repetitive tasks


@dataclass
class CommanderConfig:
    """Configuration for the Commander Agent."""

    mode: CommanderMode = CommanderMode.SUPERVISOR
    max_concurrent_tasks: int = 3
    approval_required_for: list[str] = field(
        default_factory=lambda: ["submit_report", "make_payment", "execute_code", "deploy_changes"]
    )
    auto_approve_threshold_evh: float = 50.0
    task_timeout_minutes: int = 60
    health_check_interval: int = 300


@dataclass
class TaskPlan:
    """A planned task with all execution details."""

    id: str
    opportunity_id: str
    opportunity_name: str
    platform: str
    category: str
    steps: list[dict[str, Any]]
    assigned_agent: str
    required_tools: list[str]
    estimated_duration_minutes: int
    requires_approval: bool
    approval_reason: str
    priority: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "planned"


@dataclass
class ExecutionResult:
    """Result of task execution."""

    task_id: str
    opportunity_id: str = ""  # Track which opportunity this was for
    success: bool = False
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_seconds: float = 0.0
    learning_extracted: bool = False


class CommanderAgent(BaseAgent):
    """
    OWNEX Commander Agent — the central orchestrator.

    Responsibilities:
    - Coordinate all specialized agents (Research, Coding, Browser, Review, Finance, Learning)
    - Manage the task queue from Discovery Engine
    - Handle approval workflows based on autonomy level
    - Monitor system health and agent status
    - Make strategic decisions on work prioritization
    """

    def __init__(self, config: CommanderConfig | None = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or CommanderConfig()
        self.event_bus = get_core_event_bus()

        # System components
        self.discovery_engine: DiscoveryEngine | None = None
        self.platform_manager: PlatformConnectorManager | None = None
        self.thinking_system: ThinkingSystem | None = None

        # Agent registry
        self.specialized_agents: dict[str, BaseAgent] = {}
        self.agent_health: dict[str, dict[str, Any]] = {}

        # Task management
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: dict[str, TaskPlan] = {}
        self.completed_tasks: dict[str, ExecutionResult] = {}
        self._task_counter = 0

        # Approval workflow
        self.pending_approvals: dict[str, TaskPlan] = {}
        self.approval_callbacks: list[Callable] = []

        # State
        self._running = False
        self._main_loop_task: asyncio.Task | None = None
        self._health_task: asyncio.Task | None = None

        logger.info("CommanderAgent initialized: mode=%s", self.config.mode.value)

    def _get_agent_id(self) -> AgentId:
        return AgentId.COORDINATOR

    def _get_name(self) -> str:
        return "OWNEX Commander"

    def _get_capabilities(self) -> list[str]:
        return [
            "orchestrate_agents",
            "manage_task_queue",
            "approval_workflow",
            "strategic_prioritization",
            "health_monitoring",
            "resource_allocation",
        ]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [
            EventType.PIPELINE_START,
            EventType.PIPELINE_STAGE_COMPLETED,
            EventType.PIPELINE_FAILED,
            EventType.AGENT_REGISTERED,
            EventType.AGENT_HEALTH_CHANGED,
            EventType.SYSTEM_ERROR,
            "opportunity:discovered",
            "platform:opportunities_found",
            "discovery:cycle_complete",
            "thinking:plan_created",
            "task:approval_requested",
            "task:completed",
            "task:failed",
        ]

    def handle_event(self, event: AgentEvent) -> None:
        handler_map = {
            EventType.AGENT_REGISTERED: self._on_agent_registered,
            EventType.AGENT_HEALTH_CHANGED: self._on_agent_health,
            EventType.SYSTEM_ERROR: self._on_system_error,
            "opportunity:discovered": self._on_opportunity_discovered,
            "platform:opportunities_found": self._on_platform_opportunities,
            "discovery:cycle_complete": self._on_discovery_cycle_complete,
            "thinking:plan_created": self._on_plan_created,
            "task:approval_requested": self._on_approval_requested,
            "task:completed": self._on_task_completed,
            "task:failed": self._on_task_failed,
        }

        handler = handler_map.get(event.event_type)
        if handler:
            handler(event)

    # ── System Component Registration ─────────────────────────────────

    def register_discovery_engine(self, engine: DiscoveryEngine) -> None:
        """Register the discovery engine."""
        self.discovery_engine = engine
        engine.register_queued_callback(self._on_opportunity_queued)
        logger.info("Discovery engine registered")

    def register_platform_manager(self, manager: PlatformConnectorManager) -> None:
        """Register the platform connector manager."""
        self.platform_manager = manager
        logger.info("Platform manager registered")

    def register_thinking_system(self, system: ThinkingSystem) -> None:
        """Register the thinking system."""
        self.thinking_system = system
        system.register_plan_callback(self._on_daily_plan_ready)
        logger.info("Thinking system registered")

    def register_specialized_agent(self, name: str, agent: BaseAgent) -> None:
        """Register a specialized agent."""
        self.specialized_agents[name] = agent
        self.agent_health[name] = {
            "status": "idle",
            "last_seen": datetime.now(UTC),
            "tasks_completed": 0,
            "tasks_failed": 0,
        }
        logger.info("Registered specialized agent: %s", name)

    def register_approval_callback(self, callback: Callable) -> None:
        """Register callback for approval requests."""
        self.approval_callbacks.append(callback)

    # ── Main Control Loop ─────────────────────────────────────────────

    def start(self) -> None:
        """Start the commander."""
        if self._running:
            logger.warning("Commander already running")
            return

        # Call parent start to register with event bus
        super().start()

        self._running = True
        self._main_loop_task = asyncio.create_task(self._main_loop())
        self._health_task = asyncio.create_task(self._health_monitor_loop())

        logger.info("Commander started in %s mode", self.config.mode.value)
        self.event_bus.publish("commander:started", mode=self.config.mode.value)

    def stop(self) -> None:
        """Stop the commander."""
        self._running = False

        if self._main_loop_task:
            self._main_loop_task.cancel()

        if self._health_task:
            self._health_task.cancel()

        # Stop all active tasks
        for task_id, task in self.active_tasks.items():
            asyncio.create_task(self._cancel_task(task_id, "Commander stopping"))

        # Call parent stop to unregister from event bus
        super().stop()

        logger.info("Commander stopped")
        self.event_bus.publish("commander:stopped")

    async def _main_loop(self) -> None:
        """Main orchestration loop."""
        while self._running:
            try:
                # Process task queue
                await self._process_task_queue()

                # Check active tasks for timeouts
                await self._check_task_timeouts()

                # Process pending approvals
                await self._process_approvals()

                # Periodic strategic review
                await self._strategic_review()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in commander main loop: %s", e)
                self.event_bus.publish("commander:error", error=str(e))

            await asyncio.sleep(10)  # Main loop tick

    async def _health_monitor_loop(self) -> None:
        """Periodic health monitoring."""
        while self._running:
            try:
                await self._check_system_health()
            except Exception as e:
                logger.error("Health check failed: %s", e)

            await asyncio.sleep(self.config.health_check_interval)

    # ── Task Queue Processing ─────────────────────────────────────────

    async def _on_opportunity_queued(self, opportunity: RankedOpportunity) -> None:
        """Callback when discovery engine queues an opportunity."""
        await self.task_queue.put(opportunity)
        logger.debug("Queued opportunity for commander: %s (rank=%d)", opportunity.opportunity.name, opportunity.rank)

    async def _process_task_queue(self) -> None:
        """Process queued opportunities into tasks."""
        # Limit concurrent tasks
        if len(self.active_tasks) >= self.config.max_concurrent_tasks:
            return

        try:
            # Get next opportunity (non-blocking)
            opportunity = self.task_queue.get_nowait()
        except asyncio.QueueEmpty:
            return

        # Create task plan
        task_plan = await self._create_task_plan(opportunity)

        # Check if approval required
        if task_plan.requires_approval:
            await self._request_approval(task_plan)
        else:
            await self._execute_task(task_plan)

    async def _create_task_plan(self, opportunity: RankedOpportunity) -> TaskPlan:
        """Create a detailed task plan from an opportunity."""
        self._task_counter += 1
        task_id = f"task_{self._task_counter}_{int(time.time())}"

        # Determine required agent and tools based on category
        category = opportunity.opportunity.cycle
        assigned_agent, required_tools, steps = self._plan_for_category(category, opportunity)

        # Check if approval required
        requires_approval = self._requires_approval(opportunity, category, steps)

        task_plan = TaskPlan(
            id=task_id,
            opportunity_id=opportunity.opportunity.id,
            opportunity_name=opportunity.opportunity.name,
            platform=opportunity.opportunity.source_name,
            category=category,
            steps=steps,
            assigned_agent=assigned_agent,
            required_tools=required_tools,
            estimated_duration_minutes=sum(s.get("estimated_minutes", 10) for s in steps),
            requires_approval=requires_approval,
            approval_reason=self._get_approval_reason(opportunity, steps),
            priority=5 - min(opportunity.rank // 5, 4),  # Higher rank = higher priority
        )

        return task_plan

    def _plan_for_category(
        self, category: str, opportunity: RankedOpportunity
    ) -> tuple[str, list[str], list[dict[str, Any]]]:
        """Plan steps based on opportunity category."""

        plans = {
            "security": (
                "research",
                ["browser", "terminal", "editor"],
                [
                    {"step": "analyze_scope", "tool": "browser", "estimated_minutes": 15},
                    {"step": "reconnaissance", "tool": "browser", "estimated_minutes": 30},
                    {"step": "vulnerability_research", "tool": "terminal", "estimated_minutes": 45},
                    {"step": "exploit_development", "tool": "editor", "estimated_minutes": 60},
                    {"step": "report_writing", "tool": "editor", "estimated_minutes": 30},
                    {"step": "quality_review", "tool": "review", "estimated_minutes": 15},
                ],
            ),
            "forge": (
                "coding",
                ["editor", "terminal", "git"],
                [
                    {"step": "analyze_requirements", "tool": "browser", "estimated_minutes": 15},
                    {"step": "codebase_exploration", "tool": "editor", "estimated_minutes": 30},
                    {"step": "implementation", "tool": "editor", "estimated_minutes": 120},
                    {"step": "testing", "tool": "terminal", "estimated_minutes": 30},
                    {"step": "documentation", "tool": "editor", "estimated_minutes": 15},
                    {"step": "code_review", "tool": "review", "estimated_minutes": 20},
                ],
            ),
            "pulse": (
                "coding",
                ["browser", "editor", "terminal"],
                [
                    {"step": "understand_task", "tool": "browser", "estimated_minutes": 10},
                    {"step": "data_preparation", "tool": "editor", "estimated_minutes": 20},
                    {"step": "task_execution", "tool": "editor", "estimated_minutes": 60},
                    {"step": "quality_check", "tool": "review", "estimated_minutes": 15},
                    {"step": "submission", "tool": "browser", "estimated_minutes": 10},
                ],
            ),
            "freelance": (
                "research",
                ["browser", "editor"],
                [
                    {"step": "analyze_opportunity", "tool": "browser", "estimated_minutes": 15},
                    {"step": "prepare_proposal", "tool": "editor", "estimated_minutes": 30},
                    {"step": "portfolio_update", "tool": "editor", "estimated_minutes": 15},
                    {"step": "submit_proposal", "tool": "browser", "estimated_minutes": 10},
                ],
            ),
        }

        return plans.get(
            category,
            (
                "research",
                ["browser"],
                [
                    {"step": "generic_analysis", "tool": "browser", "estimated_minutes": 30},
                ],
            ),
        )

    def _requires_approval(self, opportunity: RankedOpportunity, steps: list[dict]) -> bool:
        """Determine if task requires human approval."""
        # Check mode
        if self.config.mode == CommanderMode.OBSERVER:
            return True
        if self.config.mode == CommanderMode.PREPARER:
            return True

        # Check for high-risk actions
        for step in steps:
            if step.get("tool") in self.config.approval_required_for:
                return True

        # Check EVH threshold for auto-approval
        if opportunity.evh >= self.config.auto_approve_threshold_evh:
            return False

        # Check if first time on this platform
        platform = opportunity.opportunity.source_name
        completed_platforms = set()
        # Note: This is synchronous check - in async context we'd fetch more detail
        # For now, use simple heuristic
        for task_id, completed_task in self.completed_tasks.items():
            if hasattr(completed_task, "opportunity_id") and completed_task.opportunity_id:
                # Check if this task's platform matches
                if completed_task.opportunity_id and platform in str(completed_task.opportunity_id):
                    completed_platforms.add(platform)
        if platform not in completed_platforms:
            return True

        return True  # Default to requiring approval

    def _get_approval_reason(self, opportunity: RankedOpportunity, steps: list[dict]) -> str:
        """Generate approval reason."""
        reasons = []

        if self.config.mode in (CommanderMode.OBSERVER, CommanderMode.PREPARER):
            reasons.append(f"Mode is {self.config.mode.value}")

        if opportunity.evh < self.config.auto_approve_threshold_evh:
            reasons.append(
                f"EVH (${opportunity.evh:.0f}/hr) below auto-approve threshold (${self.config.auto_approve_threshold_evh}/hr)"
            )

        for step in steps:
            if step.get("tool") in self.config.approval_required_for:
                reasons.append(f"Requires {step['tool']} tool")

        return "; ".join(reasons) if reasons else "Standard approval required"

    async def _execute_task(self, task_plan: TaskPlan) -> None:
        """Execute a task plan."""
        task_plan.status = "running"
        self.active_tasks[task_plan.id] = task_plan

        logger.info("Executing task %s: %s", task_plan.id, task_plan.opportunity_name)
        self.event_bus.publish("task:started", task_id=task_plan.id, plan=task_plan.__dict__)

        start_time = time.time()
        agent = self.specialized_agents.get(task_plan.assigned_agent)

        if not agent:
            result = ExecutionResult(
                task_id=task_plan.id,
                opportunity_id=task_plan.opportunity_id,
                success=False,
                output={},
                error=f"Agent {task_plan.assigned_agent} not registered",
                duration_seconds=time.time() - start_time,
            )
        else:
            try:
                # Delegate to specialized agent
                result = await asyncio.wait_for(
                    self._delegate_to_agent(agent, task_plan),
                    timeout=self.config.task_timeout_minutes * 60,
                )
            except TimeoutError:
                result = ExecutionResult(
                    task_id=task_plan.id,
                    opportunity_id=task_plan.opportunity_id,
                    success=False,
                    output={},
                    error=f"Task timed out after {self.config.task_timeout_minutes} minutes",
                    duration_seconds=time.time() - start_time,
                )
            except Exception as e:
                result = ExecutionResult(
                    task_id=task_plan.id,
                    opportunity_id=task_plan.opportunity_id,
                    success=False,
                    output={},
                    error=str(e),
                    duration_seconds=time.time() - start_time,
                )

        # Record result
        self.completed_tasks[task_plan.id] = result
        del self.active_tasks[task_plan.id]

        # Update agent health
        if agent:
            health = self.agent_health.get(task_plan.assigned_agent, {})
            if result.success:
                health["tasks_completed"] = health.get("tasks_completed", 0) + 1
            else:
                health["tasks_failed"] = health.get("tasks_failed", 0) + 1
            health["last_seen"] = datetime.now(UTC)

        # Emit completion event
        if result.success:
            self.event_bus.publish("task:completed", task_id=task_plan.id, result=result.__dict__)
        else:
            self.event_bus.publish("task:failed", task_id=task_plan.id, error=result.error)

        # Trigger learning
        if self.thinking_system:
            self.thinking_system.record_task_result(
                task_id=task_plan.id,
                task_type=task_plan.category,
                platform=task_plan.platform,
                success=result.success,
                details={
                    "what_worked": result.output.get("what_worked", []) if result.success else [],
                    "what_failed": [result.error] if not result.success else [],
                    "improvements": result.output.get("improvements", []),
                    "confidence": 0.8 if result.success else 0.5,
                    "tags": [task_plan.category, task_plan.platform],
                },
            )

    async def _delegate_to_agent(self, agent: BaseAgent, task_plan: TaskPlan) -> ExecutionResult:
        """Delegate task to specialized agent."""
        # In a real implementation, this would call the agent's execute method
        # For now, we simulate with the agent's event handling

        agent_event = AgentEvent(
            event_type=EventType.PIPELINE_START,
            source=AgentId.COORDINATOR,
            target=agent._get_agent_id(),
            correlation_id=task_plan.id,
            payload={
                "task_plan": task_plan.__dict__,
                "opportunity_id": task_plan.opportunity_id,
            },
        )

        agent.handle_event(agent_event)

        # Wait for completion (simplified - real impl would use event bus)
        await asyncio.sleep(1)

        return ExecutionResult(
            task_id=task_plan.id,
            opportunity_id=task_plan.opportunity_id,
            success=True,
            output={"status": "delegated", "agent": task_plan.assigned_agent},
            duration_seconds=1.0,
        )

    async def _cancel_task(self, task_id: str, reason: str) -> None:
        """Cancel an active task."""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = "cancelled"
            del self.active_tasks[task_id]
            logger.info("Cancelled task %s: %s", task_id, reason)
            self.event_bus.publish("task:cancelled", task_id=task_id, reason=reason)

    async def _check_task_timeouts(self) -> None:
        """Check for timed out tasks."""
        now = time.time()
        for task_id, task in list(self.active_tasks.items()):
            # In real implementation, track start time
            pass

    # ── Approval Workflow ────────────────────────────────────────────

    async def _request_approval(self, task_plan: TaskPlan) -> None:
        """Request approval for a task."""
        self.pending_approvals[task_plan.id] = task_plan
        task_plan.status = "awaiting_approval"

        logger.info("Approval requested for task %s: %s", task_plan.id, task_plan.approval_reason)

        # Notify approval callbacks
        for callback in self.approval_callbacks:
            try:
                await callback(task_plan)
            except Exception as e:
                logger.error("Approval callback failed: %s", e)

        self.event_bus.publish("approval:requested", task_id=task_plan.id, plan=task_plan.__dict__)

    async def _process_approvals(self) -> None:
        """Process pending approvals (auto-approve in autonomous mode)."""
        if self.config.mode == CommanderMode.AUTONOMOUS:
            # Auto-approve high EVH tasks
            for task_id, task in list(self.pending_approvals.items()):
                # Find the original opportunity to check EVH
                if self.discovery_engine:
                    queued = await self.discovery_engine.get_queued_opportunities()
                    for opp in queued:
                        if opp.opportunity.id == task.opportunity_id:
                            if opp.evh >= self.config.auto_approve_threshold_evh:
                                await self._approve_task(task_id)
                                break

    async def approve_task(self, task_id: str, approved: bool, reason: str = "") -> bool:
        """Approve or reject a pending task."""
        if task_id not in self.pending_approvals:
            return False

        task = self.pending_approvals.pop(task_id)

        if approved:
            await self._approve_task(task_id)
        else:
            await self._reject_task(task_id, reason)

        return True

    async def _approve_task(self, task_id: str) -> None:
        """Approve and execute a task."""
        if task_id in self.pending_approvals:
            task = self.pending_approvals.pop(task_id)
            task.status = "approved"
            logger.info("Task %s approved", task_id)
            await self._execute_task(task)

    async def _reject_task(self, task_id: str, reason: str) -> None:
        """Reject a task."""
        if task_id in self.pending_approvals:
            task = self.pending_approvals.pop(task_id)
            task.status = "rejected"
            logger.info("Task %s rejected: %s", task_id, reason)

            if self.discovery_engine:
                # Find and reject the opportunity
                queued = await self.discovery_engine.get_queued_opportunities()
                for opp in queued:
                    if opp.opportunity.id == task.opportunity_id:
                        await self.discovery_engine.reject_opportunity(opp, reason)
                        break

            self.event_bus.publish("task:rejected", task_id=task_id, reason=reason)

    # ── Strategic Review ─────────────────────────────────────────────

    async def _strategic_review(self) -> None:
        """Periodic strategic review of system state."""
        # This runs periodically to make high-level decisions
        pass

    async def _check_system_health(self) -> None:
        """Check health of all components."""
        health_issues = []

        # Check discovery engine
        if self.discovery_engine:
            dh = await self.discovery_engine.health_check()
            if not dh["healthy"]:
                health_issues.extend([f"Discovery: {i}" for i in dh["issues"]])

        # Check thinking system
        if self.thinking_system:
            th = await self.thinking_system.health_check()
            if not th["healthy"]:
                health_issues.extend([f"Thinking: {i}" for i in th["issues"]])

        # Check agents
        for name, health in self.agent_health.items():
            if health.get("status") == "error":
                health_issues.append(f"Agent {name}: error status")
            age = (datetime.now(UTC) - health.get("last_seen", datetime.now(UTC))).total_seconds()
            if age > 600:  # 10 minutes
                health_issues.append(f"Agent {name}: no heartbeat for {age:.0f}s")

        if health_issues:
            logger.warning("Health issues detected: %s", health_issues)
            self.event_bus.publish("commander:health_issues", issues=health_issues)

    # ── Event Handlers ──────────────────────────────────────────────

    def _on_agent_registered(self, event: AgentEvent) -> None:
        """Handle agent registration."""
        agent_id = event.payload.get("agent_id", "unknown")
        capabilities = event.payload.get("capabilities", [])

        self.agent_health[agent_id] = {
            "status": "idle",
            "last_seen": event.timestamp,
            "capabilities": capabilities,
            "tasks_completed": 0,
            "tasks_failed": 0,
        }

        logger.info("Agent registered: %s (%s)", agent_id, capabilities)

    def _on_agent_health(self, event: AgentEvent) -> None:
        """Handle agent health update."""
        agent_id = event.payload.get("agent_id", "unknown")
        status = event.payload.get("status", "unknown")

        if agent_id in self.agent_health:
            self.agent_health[agent_id].update(
                {
                    "status": status,
                    "last_seen": event.timestamp,
                }
            )

    def _on_system_error(self, event: AgentEvent) -> None:
        """Handle system error."""
        logger.warning("System error from %s: %s", event.source, event.payload.get("error", ""))

    def _on_opportunity_discovered(self, event: AgentEvent) -> None:
        """Handle new opportunity from discovery."""
        # Opportunities flow through discovery engine queue
        pass

    def _on_platform_opportunities(self, event: AgentEvent) -> None:
        """Handle batch of opportunities from platform."""
        opportunities = event.payload.get("observations", [])
        logger.info("Platform %s found %d opportunities", event.payload.get("platform_id"), len(opportunities))

    def _on_discovery_cycle_complete(self, event: AgentEvent) -> None:
        """Handle discovery cycle completion."""
        cycle = event.payload.get("cycle", 0)
        found = event.payload.get("found", 0)
        queued = event.payload.get("queued", 0)

        logger.info("Discovery cycle %d: found=%d, queued=%d", cycle, found, queued)

    def _on_plan_created(self, event: AgentEvent) -> None:
        """Handle daily plan creation."""
        plan = event.payload.get("plan")
        if plan:
            logger.info("Daily plan created: %s", plan)

    def _on_approval_requested(self, event: AgentEvent) -> None:
        """Handle approval request (from specialized agents)."""
        # This is for when agents themselves request approval mid-task
        pass

    def _on_task_completed(self, event: AgentEvent) -> None:
        """Handle task completion from specialized agent."""
        task_id = event.payload.get("task_id")
        if task_id in self.active_tasks:
            # Task was completed by agent
            pass

    def _on_task_failed(self, event: AgentEvent) -> None:
        """Handle task failure from specialized agent."""
        task_id = event.payload.get("task_id")
        error = event.payload.get("error", "unknown")

        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = "failed"

            result = ExecutionResult(
                task_id=task_id,
                opportunity_id=task.opportunity_id,
                success=False,
                output={},
                error=error,
            )
            self.completed_tasks[task_id] = result
            del self.active_tasks[task_id]

    def _on_daily_plan_ready(self, plan: DailyPlan) -> None:
        """Callback when daily plan is ready."""
        logger.info(
            "Daily plan ready for %s: %d opportunities prioritized", plan.date, len(plan.prioritized_opportunities)
        )
        self.event_bus.publish("commander:daily_plan_ready", plan=plan.__dict__)

    # ── Public API ───────────────────────────────────────────────────

    def set_mode(self, mode: CommanderMode) -> None:
        """Change commander operating mode."""
        old_mode = self.config.mode
        self.config.mode = mode
        logger.info("Commander mode changed: %s -> %s", old_mode.value, mode.value)
        self.event_bus.publish("commander:mode_changed", old=old_mode.value, new=mode.value)

    def get_status(self) -> dict[str, Any]:
        """Get commander status."""
        return {
            "running": self._running,
            "mode": self.config.mode.value,
            "active_tasks": len(self.active_tasks),
            "queued_tasks": self.task_queue.qsize(),
            "pending_approvals": len(self.pending_approvals),
            "completed_tasks": len(self.completed_tasks),
            "registered_agents": list(self.specialized_agents.keys()),
            "agent_health": self.agent_health,
            "components": {
                "discovery_engine": self.discovery_engine is not None,
                "platform_manager": self.platform_manager is not None,
                "thinking_system": self.thinking_system is not None,
            },
        }

    def get_active_tasks(self) -> list[dict[str, Any]]:
        """Get list of active tasks."""
        return [
            {
                "id": t.id,
                "opportunity": t.opportunity_name,
                "platform": t.platform,
                "category": t.category,
                "agent": t.assigned_agent,
                "status": t.status,
                "progress": 0,  # Would track in real implementation
            }
            for t in self.active_tasks.values()
        ]

    def get_pending_approvals(self) -> list[dict[str, Any]]:
        """Get pending approval requests."""
        return [
            {
                "id": t.id,
                "opportunity": t.opportunity_name,
                "platform": t.platform,
                "reason": t.approval_reason,
                "evh": 0,  # Would fetch from opportunity
            }
            for t in self.pending_approvals.values()
        ]


# ──────────────────────────────────────────────────────────────────────────
# SINGLETON
# ──────────────────────────────────────────────────────────────────────────

_commander: CommanderAgent | None = None


def get_commander(config: CommanderConfig | None = None) -> CommanderAgent:
    """Get or create the global commander agent."""
    global _commander
    if _commander is None:
        _commander = CommanderAgent(config)
    return _commander


async def initialize_commander(
    config: CommanderConfig | None = None,
    discovery_engine: DiscoveryEngine | None = None,
    platform_manager: PlatformConnectorManager | None = None,
    thinking_system: ThinkingSystem | None = None,
) -> CommanderAgent:
    """Initialize and start the commander with all components."""
    commander = get_commander(config)

    if discovery_engine:
        commander.register_discovery_engine(discovery_engine)
    if platform_manager:
        commander.register_platform_manager(platform_manager)
    if thinking_system:
        commander.register_thinking_system(thinking_system)

    commander.start()
    return commander
