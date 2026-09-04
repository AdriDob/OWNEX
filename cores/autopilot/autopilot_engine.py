"""OWNEX Autopilot Engine - Central orchestration for 95%+ autonomous operation."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cores.autopilot.achievements.achievement_engine import AchievementEngine
from cores.autopilot.checks.daily_checks import CheckResult, DailyChecks
from cores.autopilot.config.autopilot_config import AutopilotConfig, IncomeMode, load_autopilot_config
from cores.autopilot.dashboard.autopilot_dashboard import AutopilotDashboard
from cores.autopilot.gates.human_gate import GateDecision, GateRequest, HumanGate
from cores.autopilot.goals.goal_hierarchy import GoalHierarchy
from cores.autopilot.modes.income_mode_manager import IncomeModeManager
from cores.autopilot.quant.quant_engine import QuantEngine
from cores.autopilot.velocity.capital_velocity import CapitalVelocity

logger = logging.getLogger(__name__)


@dataclass
class AutopilotStatus:
    is_running: bool = False
    started_at: datetime | None = None
    current_mode: IncomeMode = IncomeMode.BEST_INCOME
    last_cycle: datetime | None = None
    cycles_completed: int = 0
    gates_pending: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    achievements_unlocked: int = 0
    capital_velocity_usd_day: float = 0.0
    next_actions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class AutopilotEngine:
    """
    Central orchestration engine for OWNEX autonomous operation.

    Coordinates all subsystems to achieve 95%+ automation:
    - WorkBank daily cycles
    - Income Plan execution
    - Capital allocation & velocity tracking
    - Quant/Trading strategies
    - Achievement & goal tracking
    - Health monitoring & daily checks
    - Human gate management
    """

    def __init__(self, config: AutopilotConfig | None = None):
        self.config = config or load_autopilot_config()
        self.status = AutopilotStatus()
        self._running = False
        self._cycle_task: asyncio.Task | None = None
        self._health_task: asyncio.Task | None = None

        # Core subsystems (lazy init)
        self._human_gate: HumanGate | None = None
        self._income_mode_manager: IncomeModeManager | None = None
        self._achievement_engine: AchievementEngine | None = None
        self._daily_checks: DailyChecks | None = None
        self._goal_hierarchy: GoalHierarchy | None = None
        self._dashboard: AutopilotDashboard | None = None
        self._capital_velocity: CapitalVelocity | None = None
        self._quant_engine: QuantEngine | None = None

        # WorkBank integration
        self._workbank = None
        self._income_plan = None
        self._capital_engine = None
        self._coder_agent = None
        self._wear_os = None

        # Callbacks
        self._on_gate_pending: Callable[[GateRequest], None] | None = None
        self._on_check_warning: Callable[[CheckResult], None] | None = None
        self._on_achievement: Callable[[str], None] | None = None

        # Cycle timing
        self._cycle_interval = 300  # 5 minutes
        self._health_interval = 60  # 1 minute

    # --- Properties for lazy subsystem access ---

    @property
    def human_gate(self) -> HumanGate:
        if self._human_gate is None:
            self._human_gate = HumanGate(self.config)
        return self._human_gate

    @property
    def income_mode_manager(self) -> IncomeModeManager:
        if self._income_mode_manager is None:
            self._income_mode_manager = IncomeModeManager(self.config)
        return self._income_mode_manager

    @property
    def achievement_engine(self) -> AchievementEngine:
        if self._achievement_engine is None:
            self._achievement_engine = AchievementEngine(self.config)
        return self._achievement_engine

    @property
    def daily_checks(self) -> DailyChecks:
        if self._daily_checks is None:
            self._daily_checks = DailyChecks(self.config)
        return self._daily_checks

    @property
    def goal_hierarchy(self) -> GoalHierarchy:
        if self._goal_hierarchy is None:
            self._goal_hierarchy = GoalHierarchy(self.config)
        return self._goal_hierarchy

    @property
    def dashboard(self) -> AutopilotDashboard:
        if self._dashboard is None:
            self._dashboard = AutopilotDashboard(self.config)
        return self._dashboard

    @property
    def capital_velocity(self) -> CapitalVelocity:
        if self._capital_velocity is None:
            self._capital_velocity = CapitalVelocity(self.config)
        return self._capital_velocity

    @property
    def quant_engine(self) -> QuantEngine:
        if self._quant_engine is None:
            self._quant_engine = QuantEngine(self.config)
        return self._quant_engine

    # --- Lifecycle ---

    async def start(self) -> None:
        """Start the autopilot engine."""
        if self._running:
            logger.warning("Autopilot already running")
            return

        logger.info("Starting OWNEX Autopilot...")
        self._running = True
        self.status.is_running = True
        self.status.started_at = datetime.utcnow()
        try:
            self.status.current_mode = IncomeMode(self.config.automation.mode)
        except ValueError:
            self.status.current_mode = IncomeMode.BEST_INCOME

        # Initialize subsystems
        await self._initialize_subsystems()

        # Start background tasks
        self._cycle_task = asyncio.create_task(self._cycle_loop())
        self._health_task = asyncio.create_task(self._health_loop())

        # Run initial cycle
        await self._run_cycle()

        logger.info("OWNEX Autopilot started successfully")

    async def stop(self) -> None:
        """Stop the autopilot engine gracefully."""
        if not self._running:
            return

        logger.info("Stopping OWNEX Autopilot...")
        self._running = False
        self.status.is_running = False

        # Cancel background tasks
        for task in [self._cycle_task, self._health_task]:
            if task and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        logger.info("OWNEX Autopilot stopped")

    async def _initialize_subsystems(self) -> None:
        """Initialize all subsystems."""
        # Initialize income mode
        await self.income_mode_manager.set_mode(self.config.automation.mode)

        # Initialize achievement engine
        await self.achievement_engine.initialize()

        # Initialize goal hierarchy
        await self.goal_hierarchy.initialize()

        # Initialize capital velocity
        await self.capital_velocity.initialize()

        # Initialize quant engine
        await self.quant_engine.initialize()

        logger.info("All subsystems initialized")

    # --- Main Loops ---

    async def _cycle_loop(self) -> None:
        """Main autopilot cycle - runs every 5 minutes."""
        while self._running:
            try:
                await self._run_cycle()
            except Exception as e:
                logger.error(f"Autopilot cycle error: {e}")
                self.status.errors.append(f"{datetime.utcnow().isoformat()}: {e}")
                if len(self.status.errors) > 100:
                    self.status.errors = self.status.errors[-100:]

            await asyncio.sleep(self._cycle_interval)

    async def _health_loop(self) -> None:
        """Health monitoring loop - runs every minute."""
        while self._running:
            try:
                await self._run_health_checks()
            except Exception as e:
                logger.error(f"Health check error: {e}")

            await asyncio.sleep(self._health_interval)

    async def _run_cycle(self) -> None:
        """Execute one full autopilot cycle."""
        cycle_start = time.time()
        self.status.last_cycle = datetime.utcnow()
        self.status.cycles_completed += 1

        logger.debug(f"Starting autopilot cycle #{self.status.cycles_completed}")

        # 1. Run daily checks (once per day at 06:00, but check every cycle)
        check_results = await self.daily_checks.run_all()
        self._update_check_stats(check_results)

        # 2. Run WorkBank daily cycle if needed
        await self._run_workbank_cycle()

        # 3. Update Income Plan & get next actions
        next_actions = await self._update_income_plan()
        self.status.next_actions = next_actions[:5]

        # 4. Update Capital Velocity
        velocity = await self.capital_velocity.update()
        self.status.capital_velocity_usd_day = velocity.net_capital_added

        # 4b. Update Quant Engine
        await self.quant_engine.run_cycle()

        # 5. Check for pending human gates
        pending_gates = self.human_gate.get_pending_gates()
        self.status.gates_pending = len(pending_gates)

        # 6. Check achievements
        new_achievements = await self.achievement_engine.check_and_unlock()
        if new_achievements:
            self.status.achievements_unlocked += len(new_achievements)
            for ach in new_achievements:
                if self._on_achievement:
                    self._on_achievement(ach)

        # 7. Update goals progress
        await self.goal_hierarchy.update_progress()

        # 8. Check for gate warnings
        for gate in pending_gates:
            if (
                gate.waiting_since
                and (datetime.utcnow() - gate.waiting_since).total_seconds() > 3600
                and self._on_check_warning
            ):
                self._on_check_warning(
                    CheckResult(
                        name=f"gate_stale_{gate.gate_type.value}",
                        passed=False,
                        message=f"Gate {gate.gate_type.value} pending > 1hr: {gate.description}",
                        severity="warning",
                    )
                )

        cycle_duration = time.time() - cycle_start
        logger.debug(f"Autopilot cycle completed in {cycle_duration:.2f}s")

    async def _run_health_checks(self) -> None:
        """Quick health checks every minute."""
        # Check scheduler
        # Check event bus
        # Check AI providers
        # Check critical alerts
        pass

    async def _run_workbank_cycle(self) -> None:
        """Run WorkBank daily cycle if not already run today."""
        if self._workbank is None:
            try:
                from cores.direct_work_engine.workbank import get_workbank

                self._workbank = get_workbank()
            except Exception as e:
                logger.warning(f"WorkBank not available: {e}")
                return

        # Check if cycle already ran today
        try:
            # Check if WorkBank has get_last_cycle_date method
            if hasattr(self._workbank, "get_last_cycle_date"):
                last_cycle = self._workbank.get_last_cycle_date()
            elif hasattr(self._workbank, "last_cycle_date"):
                last_cycle = self._workbank.last_cycle_date
            else:
                # Fallback: check if cycle ran today by checking state
                last_cycle = None

            today = datetime.utcnow().date()

            if last_cycle != today:
                self._workbank.daily_cycle(opportunities=[])
                # Trigger achievement check
                await self.achievement_engine.check_workbank_milestones()
        except Exception as e:
            logger.error(f"WorkBank cycle error: {e}")

    async def _update_income_plan(self) -> list[str]:
        """Update income plan and return next actions."""
        if self._income_plan is None:
            try:
                from cores.direct_work_engine.income_plan import UnifiedIncomePlan

                self._income_plan = UnifiedIncomePlan()
            except Exception as e:
                logger.warning(f"Income plan engine not available: {e}")
                return ["Income plan not available"]

        plan = self._income_plan.build()

        # Extract next actions
        actions = []
        if plan.get("next_action"):
            actions.append(str(plan["next_action"]))
        if plan.get("phases", {}).get("now"):
            for item in plan["phases"]["now"][:3]:
                actions.append(f"Execute: {item.get('title', 'Unknown')}")

        return actions

    def _update_check_stats(self, results: list[CheckResult]) -> None:
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        self.status.checks_passed = passed
        self.status.checks_failed = failed

        for result in results:
            if not result.passed and result.severity in ("critical", "warning") and self._on_check_warning:
                self._on_check_warning(result)

    # --- Public API ---

    def get_status(self) -> AutopilotStatus:
        return self.status

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get complete dashboard data for frontend."""
        return self.dashboard.get_full_state(
            status=self.status,
            config=self.config,
            human_gate=self.human_gate,
            achievement_engine=self.achievement_engine,
            goal_hierarchy=self.goal_hierarchy,
            capital_velocity=self.capital_velocity,
            quant_engine=self.quant_engine,
        )

    async def set_income_mode(self, mode: IncomeMode) -> None:
        """Switch income mode instantly."""
        await self.income_mode_manager.set_mode(mode)
        self.config.automation.mode = mode.value
        self.status.current_mode = mode
        logger.info(f"Income mode changed to: {mode.value}")

    async def approve_gate(self, gate_id: str, decision: GateDecision, notes: str = "") -> bool:
        """Approve or reject a pending human gate."""
        return await self.human_gate.resolve_gate(gate_id, decision, notes)

    async def trigger_workbank_cycle(self) -> dict[str, Any]:
        """Manually trigger a WorkBank cycle."""
        if self._workbank is None:
            try:
                from cores.direct_work_engine.workbank import get_workbank

                self._workbank = get_workbank()
            except Exception as e:
                logger.warning(f"WorkBank not available: {e}")
                return {"error": str(e)}

        try:
            # daily_cycle is not async, returns dict directly
            result = self._workbank.daily_cycle(opportunities=[])
        except TypeError as e:
            # Handle case where daily_cycle requires opportunities parameter
            if "opportunities" in str(e):
                result = self._workbank.daily_cycle(opportunities=[])
            else:
                raise
        await self.achievement_engine.check_workbank_milestones()
        return result

    async def trigger_capital_rebalance(self) -> dict[str, Any]:
        """Manually trigger capital rebalancing."""
        if self._capital_engine is None:
            try:
                from cores.capital.engine import get_capital_engine

                self._capital_engine = get_capital_engine()
            except Exception as e:
                logger.warning(f"Capital engine not available: {e}")
                return {"error": str(e)}

        try:
            result = self._capital_engine.rebalance()
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception as e:
            logger.error(f"Capital rebalance error: {e}")
            return {"error": str(e)}

    def set_gate_callback(self, callback: Callable[[GateRequest], None]) -> None:
        self._on_gate_pending = callback

    def set_check_warning_callback(self, callback: Callable[[CheckResult], None]) -> None:
        self._on_check_warning = callback

    def set_achievement_callback(self, callback: Callable[[str], None]) -> None:
        self._on_achievement = callback

    # --- Integration Setters (for wiring existing systems) ---

    def set_workbank(self, workbank: Any) -> None:
        self._workbank = workbank

    def set_income_plan(self, income_plan: Any) -> None:
        self._income_plan = income_plan

    def set_capital_engine(self, capital_engine: Any) -> None:
        self._capital_engine = capital_engine

    def set_coder_agent(self, coder_agent: Any) -> None:
        self._coder_agent = coder_agent

    def set_wear_os(self, wear_os: Any) -> None:
        self._wear_os = wear_os
        self.human_gate.set_wear_os(wear_os)


# --- Singleton Instance ---

_autopilot_instance: AutopilotEngine | None = None


def get_autopilot(config: AutopilotConfig | None = None) -> AutopilotEngine:
    """Get or create the singleton AutopilotEngine instance."""
    global _autopilot_instance
    if _autopilot_instance is None:
        _autopilot_instance = AutopilotEngine(config)
    return _autopilot_instance


async def start_autopilot(config: AutopilotConfig | None = None) -> AutopilotEngine:
    """Start the autopilot singleton."""
    autopilot = get_autopilot(config)
    await autopilot.start()
    return autopilot


async def stop_autopilot() -> None:
    """Stop the autopilot singleton."""
    global _autopilot_instance
    if _autopilot_instance:
        await _autopilot_instance.stop()
        _autopilot_instance = None
