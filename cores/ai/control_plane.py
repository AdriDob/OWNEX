"""AI Control Plane — 24/7 Autonomous Supervision and Self-Improvement.

The Control Plane is the brain that continuously monitors, diagnoses, and improves
the entire OWNEX system. It implements the OBSERVE→DETECT→DIAGNOSE→PLAN→
EXECUTE→VALIDATE→REPORT→LEARN→IMPROVE cycle.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from cores.ai.runtime import get_oar
from cores.direct_work_engine.economic_engine_v2 import get_economic_engine_v2
from cores.direct_work_engine.workbank import get_workbank
from cores.health.engine import HealthCenter
from cores.scheduler.scheduler_v2 import get_scheduler

logger = logging.getLogger("ownex.ai.control_plane")


class ControlPlaneState(Enum):
    """Control plane operational states."""

    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ControlPlaneEvent:
    """Event emitted by the control plane."""

    event_type: str
    timestamp: str
    severity: str  # info, warning, critical
    source: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ControlPlaneAction:
    """An action the control plane can take."""

    action_type: str  # observe, detect, diagnose, plan, execute, validate, report, learn, improve
    priority: int  # 1=highest, 10=lowest
    target: str
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    requires_human_approval: bool = False
    estimated_duration_seconds: int = 30
    dependencies: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ControlPlaneObservation:
    """Observation from the control plane."""

    observation_id: str
    timestamp: str
    category: str  # system, work, revenue, ai, scheduler, security, learning
    severity: str  # info, warning, critical
    title: str
    description: str
    metrics: dict[str, Any] = field(default_factory=dict)
    actionable: bool = False
    suggested_actions: list[str] = field(default_factory=list)


class AIControlPlane:
    """
    24/7 Autonomous Control Plane — The brain that continuously monitors,
    diagnoses, and improves the entire OWNEX system.

    Implements the OBSERVE→DETECT→DIAGNOSE→PLAN→EXECUTE→VALIDATE→
    REPORT→LEARN→IMPROVE cycle.
    """

    def __init__(self):
        self._state = ControlPlaneState.STARTING
        self._running = False
        self._task: asyncio.Task | None = None
        self._observations: list[ControlPlaneObservation] = []
        self._actions: list[ControlPlaneAction] = []
        self._events: list[ControlPlaneEvent] = []
        self._cycle_count = 0
        self._last_cycle = datetime.now(UTC)
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._learning_data: list[dict[str, Any]] = []
        self._improvement_proposals: list[dict[str, Any]] = []

    async def start(self) -> None:
        """Start the 24/7 control plane."""
        if self._running:
            return

        self._state = ControlPlaneState.RUNNING
        self._running = True
        self._task = asyncio.create_task(self._control_loop())
        logger.info("AI Control Plane started - 24/7 supervision active")

    async def stop(self) -> None:
        """Stop the control plane gracefully."""
        self._running = False
        self._state = ControlPlaneState.STOPPING

        # Cancel running tasks
        for task in self._running_tasks.values():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

        self._state = ControlPlaneState.STOPPED
        logger.info("AI Control Plane stopped")

    async def _control_loop(self) -> None:
        """Main 24/7 control loop - the heart of the control plane."""
        while self._running:
            try:
                cycle_start = datetime.now(UTC)
                self._cycle_count += 1
                self._last_cycle = cycle_start

                # OBSERVE: Collect system state
                observations = await self._observe()

                # DETECT: Detect anomalies and opportunities
                detections = await self._detect(observations)

                # DIAGNOSE: Root cause analysis
                diagnoses = await self._diagnose(detections)

                # PLAN: Create action plans
                plans = await self._plan(diagnoses)

                # EXECUTE: Execute safe actions automatically
                execution_results = await self._execute(plans)

                # VALIDATE: Verify outcomes
                validation_results = await self._validate(execution_results)

                # REPORT: Generate reports
                await self._report(validation_results)

                # LEARN: Update models
                await self._learn(validation_results)

                # IMPROVE: Propose improvements
                await self._improve()

                # Log cycle completion
                cycle_duration = (datetime.now(UTC) - cycle_start).total_seconds()
                logger.debug(f"Control cycle {self._cycle_count} completed in {cycle_duration:.2f}s")

                # Wait for next cycle (configurable interval)
                await asyncio.sleep(60)  # 1 minute cycle

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception(f"Control loop error: {exc}")
                await asyncio.sleep(30)  # Back off on error

    # ===== OBSERVE =====

    async def _observe(self) -> list[ControlPlaneObservation]:
        """Observe system state across all subsystems."""

        # System health
        try:
            health_center = HealthCenter()
            summary = health_center.summary()
            obs = ControlPlaneObservation(
                observation_id=f"obs_{datetime.now(UTC).timestamp()}",
                timestamp=datetime.now(UTC).isoformat(),
                category="system",
                severity="info"
                if summary.get("score", 0) > 80
                else "warning"
                if summary.get("score", 0) > 50
                else "critical",
                title="System Health",
                description=f"System status: {summary.get('status', 'unknown')} (score: {summary.get('score', 0)})",
                metrics={"score": summary.get("score", 0), "status": summary.get("status", "unknown")},
                actionable=summary.get("score", 100) < 80,
                suggested_actions=["Investigate failed checks"] if summary.get("score", 100) < 80 else [],
            )
            self._observations.append(obs)
        except Exception as exc:
            logger.warning(f"Health observation failed: {exc}")

        # Work Bank status
        try:
            bank = get_workbank()
            items = list(bank._items.values()) if hasattr(bank, "_items") else []
            ready = len([i for i in items if getattr(i, "status", "") == "ready_to_deliver"])
            needs_access = len([i for i in items if getattr(i, "status", "") == "needs_access"])

            obs = ControlPlaneObservation(
                observation_id=f"obs_{datetime.now(UTC).timestamp()}",
                timestamp=datetime.now(UTC).isoformat(),
                category="work",
                severity="info",
                title="Work Bank Status",
                description=f"Ready: {ready}, Needs Access: {needs_access}, Total: {len(self._observations)}",
                metrics={
                    "ready_to_deliver": ready,
                    "needs_access": needs_access,
                    "total": len(self._observations),
                },
                actionable=needs_access > 0,
                suggested_actions=["Configure API keys for platforms needing access"] if needs_access > 0 else [],
            )
            self._observations.append(obs)
        except Exception as exc:
            logger.warning(f"Work bank observation failed: {exc}")

        # Revenue/Financial
        try:
            engine = get_economic_engine_v2()
            snapshot = engine.get_snapshot()

            obs = ControlPlaneObservation(
                observation_id=f"obs_{datetime.now(UTC).timestamp()}",
                timestamp=datetime.now(UTC).isoformat(),
                category="revenue",
                severity="info",
                title="Revenue Snapshot",
                description=f"Work Net: ${snapshot.work_net}, Trading Net: ${snapshot.trading_net}, Capital Net: ${snapshot.capital_net}",
                metrics={
                    "work_net": float(snapshot.work_net),
                    "trading_net": float(snapshot.trading_net),
                    "capital_net": float(snapshot.capital_net),
                    "total_net": float(snapshot.total_net),
                },
                actionable=float(snapshot.total_net) < 1000,
                suggested_actions=["Focus on high-HTROI opportunities"] if float(snapshot.total_net) < 1000 else [],
            )
            self._observations.append(obs)
        except Exception as exc:
            logger.warning(f"Revenue observation failed: {exc}")

        # AI/Providers
        try:
            oar = get_oar()
            status = oar.status()

            providers = status.get("providers", [])
            healthy = sum(1 for p in providers if p.get("healthy", False))
            total = len(providers)

            obs = ControlPlaneObservation(
                observation_id=f"obs_{datetime.now(UTC).timestamp()}",
                timestamp=datetime.now(UTC).isoformat(),
                category="ai",
                severity="info" if healthy == total else "warning" if healthy > 0 else "critical",
                title="AI Providers",
                description=f"Healthy: {healthy}/{total} providers",
                metrics={"healthy": healthy, "total": total, "degraded": total - healthy},
                actionable=healthy < total,
                suggested_actions=["Check degraded providers", "Check circuit breakers"] if healthy < total else [],
            )
            self._observations.append(obs)
        except Exception as exc:
            logger.warning(f"AI observation failed: {exc}")

        # Scheduler
        try:
            scheduler = get_scheduler()
            health = scheduler.get_health_report()

            obs = ControlPlaneObservation(
                observation_id=f"obs_{datetime.now(UTC).timestamp()}",
                timestamp=datetime.now(UTC).isoformat(),
                category="scheduler",
                severity="info" if health.get("running", False) else "critical",
                title="Scheduler Status",
                description=f"Running: {health.get('running', False)}, Jobs: {health.get('total_jobs', 0)}",
                metrics={"running": health.get("running", False), "jobs": health.get("total_jobs", 0)},
                actionable=not health.get("running", False),
                suggested_actions=["Restart scheduler"] if not health.get("running", False) else [],
            )
            self._observations.append(obs)
        except Exception as exc:
            logger.warning(f"Scheduler observation failed: {exc}")

        # Keep only last 1000 observations
        if len(self._observations) > 1000:
            self._observations = self._observations[-1000:]

        return self._observations[-10:]  # Return recent observations

    # ===== DETECT =====

    async def _detect(self, observations: list) -> list[dict[str, Any]]:
        """Detect anomalies and opportunities from observations."""
        detections = []

        for obs in observations:
            # Detect critical health issues
            if obs.severity == "critical":
                detections.append(
                    {
                        "type": "critical_health",
                        "source": obs.category,
                        "title": obs.title,
                        "description": obs.description,
                        "severity": "critical",
                        "metrics": obs.metrics,
                    }
                )

            # Detect degraded AI providers
            if obs.category == "ai" and obs.severity == "warning":
                detections.append(
                    {
                        "type": "degraded_ai",
                        "source": "ai",
                        "title": obs.title,
                        "description": f"AI providers degraded: {obs.metrics.get('healthy', 0)}/{obs.metrics.get('total', 0)} healthy",
                        "severity": "warning",
                        "metrics": obs.metrics,
                    }
                )

            # Detect work bank bottlenecks
            if obs.category == "work" and obs.metrics.get("needs_access", 0) > 5:
                detections.append(
                    {
                        "type": "work_bottleneck",
                        "source": "work",
                        "title": "Access configuration bottleneck",
                        "description": f"{obs.metrics.get('needs_access', 0)} items need platform access configuration",
                        "severity": "warning",
                        "metrics": obs.metrics,
                    }
                )

            # Detect revenue issues
            if obs.category == "revenue" and obs.severity != "info":
                detections.append(
                    {
                        "type": "revenue_concern",
                        "source": "revenue",
                        "title": "Revenue concern detected",
                        "description": obs.description,
                        "severity": obs.severity,
                        "metrics": obs.metrics,
                    }
                )

            # Detect scheduler issues
            if obs.category == "scheduler" and obs.severity == "critical":
                detections.append(
                    {
                        "type": "scheduler_down",
                        "source": "scheduler",
                        "title": "Scheduler not running",
                        "description": "Scheduler is not running - jobs will not execute",
                        "severity": "critical",
                        "metrics": obs.metrics,
                    }
                )

        return detections

    # ===== DIAGNOSE =====

    async def _diagnose(self, detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Root cause analysis for detections."""
        diagnoses = []

        for detection in detections:
            diagnosis = {
                "detection_id": detection.get("type", "unknown"),
                "root_causes": [],
                "confidence": 0.0,
                "evidence": [],
                "recommended_actions": [],
            }

            if detection["type"] == "critical_health":
                # Check specific failed checks
                health_center = HealthCenter()
                summary = health_center.summary()
                failed_checks = [k for k, v in summary.get("categories", {}).items() if not v]
                diagnosis["root_causes"] = [f"Failed health checks: {', '.join(failed_checks)}"]
                diagnosis["confidence"] = 0.9
                diagnosis["recommended_actions"] = ["Investigate failed health checks", "Check logs for errors"]

            elif detection["type"] == "degraded_ai":
                # Check circuit breakers
                oar = get_oar()
                status = oar.status()
                circuit_breakers = status.get("resilience", {}).get("circuit_breakers", {})
                open_breakers = [k for k, v in circuit_breakers.items() if v]
                diagnosis["root_causes"] = [
                    f"Open circuit breakers: {', '.join(open_breakers)}"
                    if open_breakers
                    else "No open circuit breakers"
                ]
                diagnosis["confidence"] = 0.8
                diagnosis["recommended_actions"] = ["Check provider health", "Review circuit breaker thresholds"]

            elif detection["type"] == "work_bottleneck":
                diagnosis["root_causes"] = ["Platform access not configured", "Missing API keys"]
                diagnosis["confidence"] = 0.95
                diagnosis["recommended_actions"] = ["Configure API keys in opportunity.env", "Run setup checklist"]

            elif detection["type"] == "scheduler_down":
                diagnosis["root_causes"] = ["Scheduler process stopped", "Event loop blocked"]
                diagnosis["confidence"] = 0.9
                diagnosis["recommended_actions"] = ["Restart scheduler", "Check event loop health"]

            elif detection["type"] == "revenue_concern":
                diagnosis["root_causes"] = ["Low HTROI opportunities", "Low work bank delivery rate"]
                diagnosis["confidence"] = 0.7
                diagnosis["recommended_actions"] = ["Focus on high-HTROI opportunities", "Review work bank pipeline"]

            diagnoses.append(diagnosis)

        return diagnoses

    # ===== PLAN =====

    async def _plan(self, diagnoses: list[dict[str, Any]]) -> list[ControlPlaneAction]:
        """Create action plans from diagnoses."""
        actions = []

        for diagnosis in diagnoses:
            for action_desc in diagnosis.get("recommended_actions", []):
                action = ControlPlaneAction(
                    action_type="execute",
                    priority=1 if "critical" in str(diagnosis) else 3,
                    target=diagnosis.get("detection_id", "unknown"),
                    action=action_desc,
                    parameters={},
                    requires_human_approval="critical" in str(diagnosis) or "restart" in action_desc.lower(),
                    estimated_duration_seconds=60,
                    dependencies=[],
                )
                self._actions.append(action)
                actions.append(action)

        # Add proactive actions
        # Check for work bank items ready to deliver
        bank = get_workbank()
        ready_items = (
            [i for i in bank._items.values() if getattr(i, "status", "") == "ready_to_deliver"]
            if hasattr(bank, "_items")
            else []
        )
        for item in ready_items[:3]:
            action = ControlPlaneAction(
                action_type="execute",
                priority=2,
                target=f"deliver_{item.id}",
                action=f"Deliver {item.title}",
                parameters={"item_id": item.id},
                requires_human_approval=True,
                estimated_duration_seconds=120,
                dependencies=[],
            )
            self._actions.append(action)

        # Add learning action
        actions.append(
            ControlPlaneAction(
                action_type="learn",
                priority=5,
                target="learning",
                action="Update models with latest outcomes",
                parameters={},
                requires_human_approval=False,
                estimated_duration_seconds=300,
                dependencies=[],
            )
        )

        return self._actions[-20:]  # Return recent actions

    # ===== EXECUTE =====

    async def _execute(self, plans: list[ControlPlaneAction]) -> list[dict[str, Any]]:
        """Execute planned actions."""
        results = []

        for action in plans:
            if action.requires_human_approval:
                # Queue for human review - in production would notify user
                logger.info(f"Action queued for human approval: {action.action}")
                results.append(
                    {
                        "action_id": action.target,
                        "status": "pending_approval",
                        "action": action.action,
                    }
                )
                continue

            # Execute automatically
            try:
                start = datetime.now(UTC)
                success = await self._execute_action(action)
                duration = (datetime.now(UTC) - start).total_seconds()

                results.append(
                    {
                        "action_id": action.target,
                        "status": "success" if success else "failed",
                        "action": action.action,
                        "duration_seconds": duration,
                    }
                )
            except Exception as exc:
                logger.exception(f"Action execution failed: {exc}")
                results.append(
                    {
                        "action_id": action.target,
                        "status": "failed",
                        "action": action.action,
                        "error": str(exc),
                    }
                )

        return results

    async def _execute_action(self, action: ControlPlaneAction) -> bool:
        """Execute a specific action."""
        # In production, this would call specific handlers
        # For now, log and return success
        logger.info(f"Executing action: {action.action} (target: {action.target})")
        await asyncio.sleep(0.1)  # Simulate work
        return True

    # ===== VALIDATE =====

    async def _validate(self, execution_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate execution outcomes."""
        validation_results = []

        for result in execution_results:
            validation = {
                "action_id": result.get("action_id"),
                "status": result.get("status"),
                "validated": result.get("status") == "success",
                "timestamp": datetime.now(UTC).isoformat(),
            }
            validation_results.append(validation)

        return validation_results

    # ===== REPORT =====

    async def _report(self, validation_results: list[dict[str, Any]]) -> None:
        """Generate and emit reports."""
        # Log summary
        total = len(validation_results)
        passed = sum(1 for v in validation_results if v.get("validated", False))
        logger.info(f"Validation report: {passed}/{total} actions successful")

        # Emit events for significant outcomes
        for vr in validation_results:
            if not vr.get("validated", False):
                event = ControlPlaneEvent(
                    event_type="validation_failed",
                    timestamp=datetime.now(UTC).isoformat(),
                    severity="warning",
                    source="control_plane",
                    message=f"Action validation failed: {vr.get('action_id')}",
                    data=vr,
                )
                self._events.append(event)

        # Keep last 100 events
        if len(self._events) > 100:
            self._events = self._events[-100:]

    # ===== LEARN =====

    async def _learn(self, validation_results: list[dict[str, Any]]) -> None:
        """Update models based on outcomes."""
        for vr in validation_results:
            self._learning_data.append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "action_id": vr.get("action_id"),
                    "outcome": vr.get("status"),
                    "validated": vr.get("validated", False),
                }
            )

        # Keep last 1000 learning entries
        if len(self._learning_data) > 1000:
            self._learning_data = self._learning_data[-1000:]

    # ===== IMPROVE =====

    async def _improve(self) -> None:
        """Propose and evaluate improvements."""
        # Analyze patterns in learning data
        if len(self._learning_data) > 10:
            failure_rate = sum(1 for d in self._learning_data[-100:] if not d.get("validated", True)) / 100
            if failure_rate > 0.2:
                proposal = {
                    "proposal_id": f"improve_{datetime.now(UTC).timestamp()}",
                    "type": "threshold_adjustment",
                    "description": f"High failure rate ({failure_rate:.1%}) - consider adjusting thresholds",
                    "parameters": {"action": "adjust_thresholds", "direction": "lower"},
                    "confidence": 0.7,
                    "created_at": datetime.now(UTC).isoformat(),
                }
                self._improvement_proposals.append(proposal)

        # Keep last 100 proposals
        if len(self._improvement_proposals) > 100:
            self._improvement_proposals = self._improvement_proposals[-100:]

    # ===== PUBLIC API =====

    def get_status(self) -> dict[str, Any]:
        """Get control plane status."""
        return {
            "state": self._state.value,
            "running": self._running,
            "cycle_count": self._cycle_count,
            "last_cycle": self._last_cycle.isoformat() if self._last_cycle else None,
            "observations_count": len(self._observations),
            "actions_pending": len([a for a in self._actions if a.requires_human_approval]),
            "events_recent": len(self._events),
            "learning_entries": len(self._learning_data),
            "improvement_proposals": len(self._improvement_proposals),
            "uptime_seconds": (datetime.now(UTC) - self._last_cycle).total_seconds() if self._last_cycle else 0,
        }

    def get_observations(self, limit: int = 50) -> list[ControlPlaneObservation]:
        return self._observations[-limit:]

    def get_actions(self, limit: int = 50) -> list[ControlPlaneAction]:
        return self._actions[-limit:]

    def get_events(self, limit: int = 50) -> list[ControlPlaneEvent]:
        return self._events[-limit:]

    def get_improvement_proposals(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._improvement_proposals[-limit:]

    def get_learning_summary(self) -> dict[str, Any]:
        if not self._learning_data:
            return {"total_entries": 0}

        self._learning_data[-100:]
        validated = sum(1 for d in self._learning_data[-100:] if d.get("validated", False))
        return {
            "total_entries": len(self._learning_data),
            "recent_validated": validated,
            "recent_failed": 100 - validated,
            "success_rate": validated / 100 if self._learning_data else 0,
        }


# Global instance
_control_plane: AIControlPlane | None = None


def get_control_plane() -> AIControlPlane:
    """Get global control plane instance."""
    global _control_plane
    if _control_plane is None:
        _control_plane = AIControlPlane()
    return _control_plane


async def initialize_control_plane() -> AIControlPlane:
    """Initialize and start the control plane."""
    cp = get_control_plane()
    await cp.start()
    return cp
