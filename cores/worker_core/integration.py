"""WorkerCore Integration — Connects all real engines for autonomous operation.

This module wires together all the real engines:
- DirectWorkEngine (discovery, scoring, recommendation)
- AI Control Plane (24/7 supervision)
- AI Development Engine (autonomous code evolution)
- Economic Engine V2 (revenue tracking)
- OAR (AI runtime for code generation)
- Scheduler (job scheduling)
- Validation Engine (quality gate)
- Opportunity Genome (knowledge management)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cores.ai.control_plane import initialize_control_plane
from cores.ai.dev_engine import RiskLevel, initialize_dev_engine
from cores.ai.runtime import initialize_oar
from cores.direct_work_engine.economic_engine_v2 import get_economic_engine_v2
from cores.direct_work_engine.engine import get_direct_work_engine
from cores.scheduler.scheduler_v2 import get_scheduler
from cores.validation.gate import get_report_gate
from cores.worker_core.models import AutonomyLevel
from cores.worker_core.orchestrator import WorkerConfig, WorkerCore, WorkState

logger = logging.getLogger("ownex.worker_core.integration")


@dataclass(frozen=True, slots=True)
class IntegratedWorkerConfig:
    """Configuration for the fully integrated worker."""

    # Core autonomy
    autonomy_level: str = "prepare"  # discover, prepare, execute, full

    # Work settings
    max_concurrent_work: int = 3
    min_reward_usd: float = 10.0
    max_risk_score: float = 0.5
    target_monthly_usd: float = 10000.0
    min_reward_usd: float = 50.0

    # Cost controls
    max_cost_per_workflow_usd: float = 100.0
    max_cost_per_session_usd: float = 500.0

    # Checkpointing
    checkpoint_interval_seconds: int = 300  # 5 minutes

    # Safety
    human_approval_required: bool = True
    test_mode: bool = False

    # Engine enablement
    enable_direct_work: bool = True
    enable_control_plane: bool = True
    enable_dev_engine: bool = True
    enable_economic_engine: bool = True
    enable_oar: bool = True
    enable_scheduler: bool = True
    enable_quality_gate: bool = True


@dataclass
class IntegratedWorkerCore:
    """Fully integrated WorkerCore with all engines connected."""

    config: IntegratedWorkerConfig
    core: WorkerCore
    direct_work_engine: Any = None
    control_plane: Any = None
    dev_engine: Any = None
    economic_engine: Any = None
    oar: Any = None
    scheduler: Any = None
    quality_gate: Any = None

    _initialized: bool = False
    _running: bool = False
    _tasks: dict[str, asyncio.Task] = field(default_factory=dict)

    def __init__(self, config: IntegratedWorkerConfig | None = None):
        self.config = config or IntegratedWorkerConfig()
        self._tasks = {}

    async def initialize(self) -> None:
        """Initialize all engines and connect them."""
        if self._initialized:
            return

        logger.info("Initializing Integrated WorkerCore...")

        # Create base WorkerCore
        config = WorkerConfig(
            autonomy_level=AutonomyLevel[self.config.autonomy_level.upper()],
            max_concurrent_work=self.config.max_concurrent_work,
            checkpoint_interval_seconds=self.config.checkpoint_interval_seconds,
            human_approval_required=self.config.human_approval_required,
            test_mode=self.config.test_mode,
        )

        self.core = WorkerCore(config)

        # Initialize Direct Work Engine
        if self.config.enable_direct_work:
            self.direct_work_engine = get_direct_work_engine()
            self.cores.set_discovery_engine(self.direct_work_engine)
            self.cores.set_evaluation_engine(self.direct_work_engine)
            logger.info("Direct Work Engine connected")

        # Initialize AI Control Plane
        if self.config.enable_control_plane:
            self.control_plane = await initialize_control_plane()
            logger.info("AI Control Plane connected")

        # Initialize AI Development Engine
        if self.config.enable_dev_engine:
            self.dev_engine = await initialize_dev_engine()
            logger.info("AI Development Engine connected")

        # Initialize Economic Engine V2
        if self.config.enable_economic_engine:
            self.economic_engine = get_economic_engine_v2()
            logger.info("Economic Engine V2 connected")

        # Initialize OAR (AI Runtime)
        if self.config.enable_oar:
            self.oar = await initialize_oar()
            self.cores.set_ai_router(self.oar._router if self.oar._router else None)
            logger.info("OAR (AI Runtime) connected")

        # Initialize Scheduler
        if self.config.enable_scheduler:
            self.scheduler = get_scheduler()
            # Connect scheduler to WorkerCore
            self.cores._circuit_breakers["scheduler"] = None  # Scheduler has its own
            logger.info("Scheduler connected")

        # Initialize Quality Gate
        if self.config.enable_quality_gate:
            self.quality_gate = get_report_gate()
            logger.info("Quality Gate connected")

        self._initialized = True
        logger.info("Integrated WorkerCore fully initialized")

    async def start(self) -> None:
        """Start all engines and the worker cores."""
        if self._running:
            return

        if not self._initialized:
            await self.initialize()

        self._running = True

        # Start Control Plane
        if self.control_plane:
            self._tasks["control_plane"] = asyncio.create_task(self.control_plane._control_loop())
            logger.info("Control Plane started")

        # Start Dev Engine
        if self.dev_engine:
            self._tasks["dev_engine"] = asyncio.create_task(self.dev_engine.process_queue())
            logger.info("Dev Engine started")

        # Start Scheduler
        if self.scheduler:
            await self.scheduler.start()
            logger.info("Scheduler started")

        # Start Core Worker Loop
        self.cores.state = WorkState.RUNNING
        self._running = True
        self._tasks["worker_loop"] = asyncio.create_task(self.cores._main_loop())

        # Start Control Plane monitoring task
        self._tasks["monitor"] = asyncio.create_task(self._monitor_loop())

        logger.info("Integrated WorkerCore fully started")

    async def stop(self) -> None:
        """Stop all engines gracefully."""
        if not self._running:
            return

        logger.info("Stopping Integrated WorkerCore...")

        # Stop core
        await self.cores.stop()

        # Stop engines
        if self.control_plane:
            await self.control_plane.stop()

        if self.dev_engine:
            await self.dev_engine.shutdown()

        if self.scheduler:
            await self.scheduler.stop()

        if self.oar:
            await self.oar.shutdown()

        # Cancel tasks
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()

        await asyncio.gather(*[t for t in self._tasks.values()], return_exceptions=True)

        self._running = False
        logger.info("Integrated WorkerCore stopped")

    async def _monitor_loop(self) -> None:
        """Monitor all engines and report health."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                # Collect health from all engines
                health = await self._collect_health()

                # Log health summary
                logger.info(f"Health check: {health}")

                # Auto-repair if needed
                if health.get("overall") != "healthy":
                    await self._auto_repair(health)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception(f"Monitor loop error: {exc}")
                await asyncio.sleep(30)

    async def _collect_health(self) -> dict[str, Any]:
        """Collect health from all engines."""
        health = {
            "overall": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "engines": {},
        }

        # Direct Work Engine
        if self.direct_work_engine:
            status = self.direct_work_engine.get_status()
            health["engines"]["direct_work"] = {
                "status": "healthy" if status.get("running") else "unknown",
                "details": status,
            }

        # Control Plane
        if self.control_plane:
            cp_status = self.control_plane.get_status()
            health["engines"]["control_plane"] = {
                "status": "healthy" if cp_status.get("running") else "unknown",
                "details": cp_status,
            }

        # Dev Engine
        if self.dev_engine:
            de_status = self.dev_engine.get_stats()
            health["engines"]["dev_engine"] = {
                "status": "healthy" if de_status.get("total", 0) >= 0 else "unknown",
                "details": de_status,
            }

        # Scheduler
        if self.scheduler:
            sch_health = self.scheduler.get_health_report()
            health["engines"]["scheduler"] = {
                "status": "healthy" if sch_health.get("running") else "stopped",
                "details": sch_health,
            }

        # OAR
        if self.oar:
            oar_status = self.oar.status()
            health["engines"]["oar"] = {
                "status": "healthy" if oar_status.get("initialized") else "unknown",
                "details": oar_status,
            }

        # Economic Engine
        if self.economic_engine:
            ee_snapshot = self.economic_engine.get_snapshot()
            health["engines"]["economic"] = {
                "status": "healthy",
                "details": {"total_net": float(ee_snapshot.total_net)},
            }

        # Quality Gate
        if self.quality_gate:
            fail_closed = getattr(self.quality_gate, "_fail_closed", True)
            health["engines"]["quality_gate"] = {
                "status": "healthy",
                "details": {"fail_closed": fail_closed},
            }

        # Determine overall health
        engine_statuses = [e.get("status", "unknown") for e in health["engines"].values()]
        if "critical" in engine_statuses or "unhealthy" in engine_statuses:
            health["overall"] = "critical"
        elif "degraded" in engine_statuses or "unhealthy" in engine_statuses or "unknown" in engine_statuses:
            health["overall"] = "degraded"
        else:
            health["overall"] = "healthy"

        return health

    async def _auto_repair(self, health: dict[str, Any]) -> None:
        """Auto-repair unhealthy engines."""
        for engine_name, engine_health in health["engines"].items():
            if engine_health.get("status") in ("critical", "unhealthy"):
                logger.warning(f"Auto-repairing engine: {engine_name}")

                if engine_name == "scheduler" and self.scheduler:
                    try:
                        await self.scheduler.stop()
                        await asyncio.sleep(2)
                        await self.scheduler.start()
                        logger.info("Scheduler restarted")
                    except Exception as exc:
                        logger.error(f"Scheduler restart failed: {exc}")

                elif engine_name == "control_plane" and self.control_plane:
                    try:
                        await self.control_plane.stop()
                        await asyncio.sleep(2)
                        await self.control_plane.start()
                        logger.info("Control Plane restarted")
                    except Exception as exc:
                        logger.error(f"Control Plane restart failed: {exc}")

                elif engine_name == "dev_engine" and self.dev_engine:
                    try:
                        await self.dev_engine.shutdown()
                        await asyncio.sleep(1)
                        self.dev_engine = await initialize_dev_engine()
                        logger.info("Dev Engine reinitialized")
                    except Exception as exc:
                        logger.error(f"Dev Engine reinit failed: {exc}")

    async def get_status(self) -> dict[str, Any]:
        """Get comprehensive status of all engines."""
        health = await self._collect_health()

        return {
            "integrated_core": {
                "initialized": self._initialized,
                "running": self._running,
                "uptime_seconds": (datetime.now(UTC) - datetime.now(UTC)).total_seconds(),  # Will be calculated
            },
            "engines": health["engines"],
            "overall_health": health["overall"],
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def submit_work_task(
        self,
        title: str,
        description: str,
        risk: str = "medium",
        priority: int = 5,
        affected_files: list[str] | None = None,
    ) -> str:
        """Submit a work task to the Dev Engine."""
        if not self.dev_engine:
            raise RuntimeError("Dev Engine not initialized")

        task = await self.dev_engine.submit_task(
            title=title,
            description=description,
            risk=RiskLevel(risk.upper()),
            priority=priority,
            affected_files=affected_files,
        )
        return task.task_id

    async def submit_error_task(
        self,
        error: Exception,
        context: dict[str, Any],
        affected_files: list[str] | None = None,
    ) -> str:
        """Submit a task to fix an observed error."""
        if not self.dev_engine:
            raise RuntimeError("Dev Engine not initialized")

        task = await self.dev_engine.submit_error_task(error, context, affected_files)
        return task.task_id

    async def run_discovery_cycle(self) -> dict[str, Any]:
        """Run a single discovery cycle with the Direct Work Engine."""
        if not self.direct_work_engine:
            raise RuntimeError("Direct Work Engine not initialized")

        from cores.direct_work_engine.models import UserProfile

        # Build a default profile for Argentina-based user
        profile = UserProfile(
            name="Adriel",
            country="Argentina",
            languages={"es", "en"},
            skills={"python", "rust", "solidity", "typescript", "go"},
            experience_level="NONE",
            remote_only=True,
            accepts_ai_tools=True,
            availability_hours=40.0,
            has_portfolio=False,
            preferred_payment_methods=[],
            preferred_currencies=["USD"],
            preferred_employment_types=["BOUNTY", "MICROTASK"],
            preferred_categories=["DEV_BOUNTY", "AI_EVALUATION"],
            min_payment=10.0,
        )

        opportunities, ranked = await self.direct_work_engine.run_cycle(profile)

        return {
            "opportunities_found": len(opportunities),
            "recommendations": len(ranked),
            "top_recommendations": [
                {
                    "title": r.opportunity.title,
                    "platform": r.opportunity.platform.value,
                    "expected_value": r.expected_value,
                    "htroi": getattr(r, "htroi_usd_per_hour", 0),
                }
                for r in ranked[:5]
            ],
        }

    async def get_work_bank_status(self) -> dict[str, Any]:
        """Get Work Bank status."""
        from cores.direct_work_engine.workbank import get_workbank

        bank = get_workbank()
        return bank.to_dict()

    async def approve_work(self, work_id: str) -> bool:
        """Approve a work item for delivery."""
        if not self.core:
            return False
        return self.cores.approve_work(work_id)

    async def get_revenue_snapshot(self) -> dict[str, Any]:
        """Get revenue snapshot from Economic Engine."""
        if not self.economic_engine:
            return {}
        return self.economic_engine.get_snapshot().to_dict()

    async def compute_htroi(
        self,
        expected_income_usd: float,
        human_hours: float,
        confidence: float = 1.0,
    ) -> dict[str, Any] | None:
        """Compute HTROI for an opportunity."""
        from cores.direct_work_engine.economics import compute_htroi

        try:
            htroi = compute_htroi(
                expected_income_usd=expected_income_usd,
                human_hours=human_hours,
                confidence=confidence,
            )
            return {
                "roi_usd_per_hour": htroi.roi_usd_per_hour,
                "expected_income_usd": htroi.expected_income_usd,
                "human_hours_total": htroi.human_hours_total,
                "confidence_applied": htroi.confidence_applied,
            }
        except Exception as exc:
            logger.error(f"HTROI computation failed: {exc}")
            return None


# Global instance
_integrated_core: IntegratedWorkerCore | None = None


def get_integrated_core(config: IntegratedWorkerConfig | None = None) -> IntegratedWorkerCore:
    """Get global integrated worker core instance."""
    global _integrated_core
    if _integrated_core is None:
        _integrated_core = IntegratedWorkerCore(config)
    return _integrated_core


async def initialize_integrated_core(config: IntegratedWorkerConfig | None = None) -> IntegratedWorkerCore:
    """Initialize and start the integrated worker cores."""
    ic = get_integrated_core(config)
    await ic.initialize()
    await ic.start()
    return ic
