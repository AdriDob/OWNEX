"""Multi-Agent Bounty Coordinator — parallel bounty execution with priority queue.

Orchestrates multiple BountyPipeline instances in parallel with:
- Priority queue based on EVH (Expected Value per Hour)
- Max 3-5 concurrent bounties
- Automatic cleanup on timeout (>30min)
- EventBus integration for monitoring
- Stateful singleton pattern
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from queue import PriorityQueue
from typing import Any

from core.autonomy.bounty_pipeline import BountyPipeline, get_bounty_pipeline
from cores.events.event_bus import get_event_bus
from cores.opportunity.models import Opportunity

logger = logging.getLogger("cateye.agents.bounty_coordinator")


class BountyStatus(StrEnum):
    """Status of a bounty execution."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass(order=True)
class BountyTask:
    """A bounty task in the priority queue."""

    priority: float  # EVH value (higher = higher priority)
    bounty_id: str = field(compare=False)
    opportunity: Opportunity = field(compare=False)
    created_at: datetime = field(compare=False, default_factory=lambda: datetime.now(UTC))
    status: BountyStatus = field(compare=False, default=BountyStatus.QUEUED)
    result: dict[str, Any] | None = field(compare=False, default=None)
    error: str | None = field(compare=False, default=None)
    started_at: datetime | None = field(compare=False, default=None)
    completed_at: datetime | None = field(compare=False, default=None)
    metadata: dict[str, Any] = field(compare=False, default_factory=dict)


@dataclass
class CoordinatorConfig:
    """Configuration for the bounty coordinator."""

    max_concurrent: int = 3  # Max 3-5 simultaneous bounties
    timeout_minutes: int = 30  # Timeout for individual bounties
    auto_start: bool = False  # Auto-start when bounties are added
    enable_priority_queue: bool = True  # Use EVH-based priority
    cleanup_on_failure: bool = True  # Auto-cleanup failed bounties


class BountyCoordinator:
    """Multi-agent coordinator for parallel bounty execution.

    Features:
    - Priority queue based on EVH (Expected Value per Hour)
    - Max concurrent execution limit (default: 3)
    - Automatic timeout handling (default: 30min)
    - EventBus integration for monitoring
    - Stateful singleton pattern
    """

    def __init__(self, config: CoordinatorConfig | None = None) -> None:
        self.config = config or CoordinatorConfig()
        self._pipeline: BountyPipeline | None = None
        self._event_bus = get_event_bus()

        # State
        self._running = False
        self._lock = threading.Lock()
        self._queue: PriorityQueue[BountyTask] = PriorityQueue()
        self._active_tasks: dict[str, BountyTask] = {}  # bounty_id -> task
        self._completed_tasks: dict[str, BountyTask] = {}  # bounty_id -> task

        # Background scheduler
        self._scheduler_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None

        logger.info(
            "[BountyCoordinator] Initialized with max_concurrent=%d, timeout=%dmin",
            self.config.max_concurrent,
            self.config.timeout_minutes,
        )

    def _get_pipeline(self) -> BountyPipeline:
        """Get or create the bounty pipeline instance."""
        if self._pipeline is None:
            self._pipeline = get_bounty_pipeline()
        return self._pipeline

    # ── Public API ─────────────────────────────────────────────────────

    def start(self) -> dict[str, Any]:
        """Start the coordinator scheduler."""
        with self._lock:
            if self._running:
                return {"status": "already_running", "message": "Coordinator is already running"}

            self._running = True
            logger.info("[BountyCoordinator] Starting scheduler")

            # Publish event
            self._event_bus.publish(
                "coordinator:started",
                max_concurrent=self.config.max_concurrent,
                timeout_minutes=self.config.timeout_minutes,
            )

            return {"status": "started", "message": "Coordinator started successfully"}

    def stop(self) -> dict[str, Any]:
        """Stop the coordinator scheduler."""
        with self._lock:
            if not self._running:
                return {"status": "already_stopped", "message": "Coordinator is already stopped"}

            self._running = False
            logger.info("[BountyCoordinator] Stopping scheduler")

            # Cancel active tasks
            for bounty_id, task in list(self._active_tasks.items()):
                task.status = BountyStatus.CANCELLED
                task.completed_at = datetime.now(UTC)
                self._completed_tasks[bounty_id] = task
                del self._active_tasks[bounty_id]

            # Publish event
            self._event_bus.publish(
                "coordinator:stopped",
                cancelled_count=len(self._completed_tasks),
            )

            return {"status": "stopped", "message": "Coordinator stopped successfully"}

    def is_running(self) -> bool:
        """Check if the coordinator is currently running."""
        return self._running

    def add_bounty(
        self,
        bounty_id: str,
        repo: str,
        issue_number: int,
        issue_url: str,
        title: str,
        description: str = "",
        evh: float = 0.0,
        opportunity: Opportunity | None = None,
    ) -> dict[str, Any]:
        """Add a bounty to the priority queue (full signature)."""
        if opportunity is None:
            # Create minimal opportunity object if not provided
            from cores.opportunity.models import Opportunity, OpportunitySource

            opportunity = Opportunity(
                id=bounty_id,
                name=title,
                source=OpportunitySource(
                    type="platform",
                    name="algora",
                    url=issue_url,
                    confidence=0.8,
                ),
                category="oss",
                public_url=issue_url,
                metadata={"description": description},
                estimated_payout=0.0,
                estimated_effort_hours=1.0,
            )

        # Calculate EVH if not provided
        if evh == 0.0 and opportunity.estimated_payout:
            evh = opportunity.estimated_payout / max(opportunity.estimated_effort_hours, 0.1)

        task = BountyTask(
            priority=evh,
            bounty_id=bounty_id,
            opportunity=opportunity,
            metadata={
                "repo": repo,
                "issue_number": issue_number,
                "issue_url": issue_url,
            },
        )

        self._queue.put(task)

        logger.info(
            "[BountyCoordinator] Added bounty %s to queue (EVH=%.2f)",
            bounty_id,
            evh,
        )

        return {"status": "queued", "bounty_id": bounty_id, "evh": evh}

    def add_bounty_simple(
        self,
        bounty_id: str,
        opportunity: Opportunity,
    ) -> dict[str, Any]:
        """Add a bounty to the priority queue (simplified signature for scheduler)."""
        # Calculate EVH from opportunity
        evh = 0.0
        if opportunity.estimated_payout:
            evh = opportunity.estimated_payout / max(opportunity.estimated_effort_hours, 0.1)

        task = BountyTask(
            priority=evh,
            bounty_id=bounty_id,
            opportunity=opportunity,
            metadata={
                "source": "opportunity_engine",
            },
        )

        self._queue.put(task)

        logger.info(
            "[BountyCoordinator] Added bounty %s to queue (EVH=%.2f)",
            bounty_id,
            evh,
        )

        return {"status": "queued", "bounty_id": bounty_id, "evh": evh}

    def add_bounty_legacy(
        self,
        bounty_id: str,
        repo: str,
        issue_number: int,
        issue_url: str,
        title: str,
        description: str = "",
        evh: float = 0.0,
        opportunity: Opportunity | None = None,
    ) -> dict[str, Any]:
        """Add a bounty to the queue (legacy signature for backward compatibility).

        Args:
            bounty_id: Bounty ID from platform
            repo: GitHub repository (owner/repo)
            issue_number: Issue number
            issue_url: Full issue URL
            title: Issue title
            description: Issue description
            evh: Expected Value per Hour (for priority)
            opportunity: Full opportunity object (optional)

        Returns:
            Status response with task info
        """
        # Create opportunity if not provided
        if opportunity is None:
            from cores.opportunity.models import (
                EVHCalculation,
                EVHRating,
                Opportunity,
                OpportunityScore,
                OpportunitySource,
            )

            opportunity = Opportunity(
                id=bounty_id,
                name=title,
                source=OpportunitySource(
                    type="platform",
                    name="algora",
                    url=issue_url,
                    confidence=0.8,
                ),
                category="oss",
                public_url=issue_url,
                estimated_payout=evh * 2,  # Rough estimate
                estimated_effort_hours=2.0,
                score=OpportunityScore(
                    overall=0.7,
                    reward_potential=0.8,
                    scope_quality=0.7,
                    technology_overlap=0.6,
                    competition_estimate=0.5,
                    freshness=0.8,
                    reasoning=["Added via API"],
                    evh=EVHCalculation(
                        value=evh,
                        rating=EVHRating.high if evh > 100 else EVHRating.medium if evh > 50 else EVHRating.low,
                        estimated_payout=evh * 2,
                        success_probability=0.5,
                        estimated_effort_hours=2.0,
                    ),
                ),
            )

        # Determine priority (EVH-based or timestamp)
        if self.config.enable_priority_queue and opportunity.score and opportunity.score.evh:
            priority = -opportunity.score.evh.value  # Negative for max-heap behavior
        else:
            priority = -datetime.now(UTC).timestamp()  # FIFO by default

        # Create task
        task = BountyTask(
            priority=priority,
            bounty_id=bounty_id,
            opportunity=opportunity,
        )

        # Add to queue
        self._queue.put(task)

        # Store metadata for execution
        task.metadata = {
            "repo": repo,
            "issue_number": issue_number,
            "issue_url": issue_url,
            "title": title,
            "description": description,
        }

        logger.info(
            "[BountyCoordinator] Added bounty %s to queue (priority=%.2f, evh=%.2f)",
            bounty_id,
            priority,
            evh,
        )

        # Publish event
        self._event_bus.publish(
            "coordinator:bounty_queued",
            bounty_id=bounty_id,
            priority=priority,
            evh=evh,
            queue_size=self._queue.qsize(),
        )

        # Auto-start if configured
        if self.config.auto_start and not self._running:
            self.start()

        return {
            "status": "queued",
            "bounty_id": bounty_id,
            "priority": priority,
            "evh": evh,
            "queue_position": self._queue.qsize(),
        }

    def get_status(self) -> dict[str, Any]:
        """Get current coordinator status."""
        with self._lock:
            active_count = len(self._active_tasks)
            queued_count = self._queue.qsize()
            completed_count = len(self._completed_tasks)

            # Calculate stats
            completed_success = sum(1 for t in self._completed_tasks.values() if t.status == BountyStatus.COMPLETED)
            completed_failed = sum(1 for t in self._completed_tasks.values() if t.status == BountyStatus.FAILED)
            completed_timeout = sum(1 for t in self._completed_tasks.values() if t.status == BountyStatus.TIMEOUT)

            return {
                "running": self._running,
                "config": {
                    "max_concurrent": self.config.max_concurrent,
                    "timeout_minutes": self.config.timeout_minutes,
                    "auto_start": self.config.auto_start,
                    "enable_priority_queue": self.config.enable_priority_queue,
                },
                "queue": {
                    "queued": queued_count,
                    "active": active_count,
                    "completed": completed_count,
                },
                "stats": {
                    "completed_success": completed_success,
                    "completed_failed": completed_failed,
                    "completed_timeout": completed_timeout,
                },
                "active_bounties": [
                    {
                        "bounty_id": task.bounty_id,
                        "status": task.status,
                        "started_at": task.started_at.isoformat() if task.started_at else None,
                        "elapsed_minutes": (
                            (datetime.now(UTC) - task.started_at).total_seconds() / 60 if task.started_at else 0
                        ),
                    }
                    for task in self._active_tasks.values()
                ],
                "recent_completed": [
                    {
                        "bounty_id": task.bounty_id,
                        "status": task.status,
                        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                        "error": task.error,
                    }
                    for task in sorted(
                        self._completed_tasks.values(),
                        key=lambda t: t.completed_at or datetime.min.replace(tzinfo=UTC),
                        reverse=True,
                    )[:10]
                ],
            }

    # ── Execution Logic ─────────────────────────────────────────────────

    async def _execute_bounty(self, task: BountyTask) -> None:
        """Execute a single bounty task."""
        bounty_id = task.bounty_id
        metadata = getattr(task, "metadata", {})

        task.status = BountyStatus.RUNNING
        task.started_at = datetime.now(UTC)
        self._active_tasks[bounty_id] = task

        logger.info("[BountyCoordinator] Starting bounty %s", bounty_id)

        # Publish event
        self._event_bus.publish(
            "coordinator:bounty_started",
            bounty_id=bounty_id,
            repo=metadata.get("repo"),
            issue_number=metadata.get("issue_number"),
        )

        try:
            # Execute with timeout
            pipeline = self._get_pipeline()
            result = await asyncio.wait_for(
                pipeline.execute_bounty(
                    bounty_id=bounty_id,
                    repo=metadata.get("repo", ""),
                    issue_number=metadata.get("issue_number", 0),
                    issue_url=metadata.get("issue_url", ""),
                    title=metadata.get("title", ""),
                    description=metadata.get("description", ""),
                ),
                timeout=self.config.timeout_minutes * 60,
            )

            task.status = BountyStatus.COMPLETED
            task.result = {
                "success": result.success,
                "verdict": result.verdict,
                "feedback": result.feedback,
                "total_duration_seconds": result.total_duration_seconds,
                "error": result.error,
            }

            logger.info(
                "[BountyCoordinator] Bounty %s completed in %.1fs (verdict=%s)",
                bounty_id,
                result.total_duration_seconds,
                result.verdict,
            )

            # Publish event
            self._event_bus.publish(
                "coordinator:bounty_completed",
                bounty_id=bounty_id,
                verdict=result.verdict,
                duration_seconds=result.total_duration_seconds,
                success=result.success,
            )

        except TimeoutError:
            task.status = BountyStatus.TIMEOUT
            task.error = f"Timeout after {self.config.timeout_minutes} minutes"

            logger.warning("[BountyCoordinator] Bounty %s timed out", bounty_id)

            # Publish event
            self._event_bus.publish(
                "coordinator:bounty_timeout",
                bounty_id=bounty_id,
                timeout_minutes=self.config.timeout_minutes,
            )

        except Exception as e:
            task.status = BountyStatus.FAILED
            task.error = str(e)

            logger.error("[BountyCoordinator] Bounty %s failed: %s", bounty_id, e)

            # Publish event
            self._event_bus.publish(
                "coordinator:bounty_failed",
                bounty_id=bounty_id,
                error=str(e),
            )

        finally:
            task.completed_at = datetime.now(UTC)

            # Move from active to completed
            self._active_tasks.pop(bounty_id, None)
            self._completed_tasks[bounty_id] = task

            # Cleanup if configured
            if self.config.cleanup_on_failure and task.status in (BountyStatus.FAILED, BountyStatus.TIMEOUT):
                self._cleanup_bounty(task)

    def _cleanup_bounty(self, task: BountyTask) -> None:
        """Cleanup resources for a failed/timeout bounty."""
        try:
            # Cleanup repo if exists
            metadata = getattr(task, "metadata", {})
            repo = metadata.get("repo", "").replace("/", "_")
            import shutil
            from pathlib import Path

            repo_path = Path(f"/tmp/{repo}")
            if repo_path.exists():
                shutil.rmtree(repo_path, ignore_errors=True)
                logger.debug("[BountyCoordinator] Cleaned up repo: %s", repo_path)

        except Exception as e:
            logger.warning("[BountyCoordinator] Cleanup failed for bounty %s: %s", task.bounty_id, e)

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop - processes queue and manages concurrency."""
        logger.info("[BountyCoordinator] Scheduler loop started")

        while self._running:
            try:
                # Check if we can start new tasks
                if len(self._active_tasks) < self.config.max_concurrent and not self._queue.empty():
                    # Get next task from priority queue
                    task = self._queue.get_nowait()

                    # Start execution in background
                    asyncio.create_task(self._execute_bounty(task))

                # Sleep before next iteration
                await asyncio.sleep(1)

            except Exception as e:
                logger.error("[BountyCoordinator] Scheduler loop error: %s", e)
                await asyncio.sleep(5)

        logger.info("[BountyCoordinator] Scheduler loop stopped")

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of stale tasks."""
        logger.info("[BountyCoordinator] Cleanup loop started")

        while self._running:
            try:
                now = datetime.now(UTC)

                # Check for stale active tasks (shouldn't happen with timeout, but safety check)
                for bounty_id, task in list(self._active_tasks.items()):
                    if task.started_at:
                        elapsed = (now - task.started_at).total_seconds() / 60
                        if elapsed > self.config.timeout_minutes * 2:  # Double timeout as safety
                            logger.warning(
                                "[BountyCoordinator] Stale task %s detected (%.1f min), force cancelling",
                                bounty_id,
                                elapsed,
                            )
                            task.status = BountyStatus.TIMEOUT
                            task.error = "Force cancelled due to stale state"
                            task.completed_at = now
                            self._active_tasks.pop(bounty_id, None)
                            self._completed_tasks[bounty_id] = task

                # Cleanup old completed tasks (keep last 100)
                if len(self._completed_tasks) > 100:
                    # Remove oldest entries
                    sorted_tasks = sorted(
                        self._completed_tasks.items(),
                        key=lambda x: x[1].completed_at or datetime.min.replace(tzinfo=UTC),
                    )
                    for bounty_id, _ in sorted_tasks[: len(self._completed_tasks) - 100]:
                        self._completed_tasks.pop(bounty_id, None)

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error("[BountyCoordinator] Cleanup loop error: %s", e)
                await asyncio.sleep(60)

        logger.info("[BountyCoordinator] Cleanup loop stopped")


def run_coordinator_cycle() -> dict[str, Any]:
    """Scheduler job handler — run one coordinator cycle.

    This function:
    1. Gets the coordinator singleton
    2. Starts it if not running
    3. Adds pending opportunities to the queue
    4. Returns status
    """
    logger.info("[BountyCoordinator] Running scheduled cycle")

    try:
        coordinator = get_bounty_coordinator()

        # Start coordinator if not running
        if not coordinator.is_running():
            coordinator.start()
            logger.info("[BountyCoordinator] Started coordinator")

        # Get pending opportunities from the opportunity engine
        from cores.opportunity.engine import get_opportunity_engine
        from cores.opportunity.models import Opportunity, OpportunitySource

        engine = get_opportunity_engine()
        stored_opportunities = engine.get_all()

        # Add to coordinator queue
        added_count = 0
        for opp_dict in stored_opportunities:
            opp_id = str(opp_dict.get("id", ""))
            if opp_id and opp_id not in coordinator._active_tasks:
                opportunity = Opportunity(
                    id=opp_id,
                    name=str(opp_dict.get("title", "")),
                    source=OpportunitySource(
                        type="platform",
                        name=str(opp_dict.get("source", "")),
                        url="",
                        confidence=0.5,
                    ),
                    category=str(opp_dict.get("category", "oss")),
                    estimated_payout=float(opp_dict.get("reward_max", 0.0) or 0.0),
                    estimated_effort_hours=float(opp_dict.get("estimated_hours", 1.0) or 1.0),
                )
                coordinator.add_bounty_simple(opp_id, opportunity)
                added_count += 1

        # Get status
        status = coordinator.get_status()

        logger.info(
            "[BountyCoordinator] Cycle complete: added=%d, active=%d, queued=%d, completed=%d",
            added_count,
            status.get("active_count", 0),
            status.get("queued_count", 0),
            status.get("completed_count", 0),
        )

        return {
            "success": True,
            "added_count": added_count,
            "status": status,
            "message": f"Added {added_count} bounties to coordinator queue",
        }

    except Exception as e:
        logger.error("[BountyCoordinator] Scheduled cycle failed: %s", e)
        return {
            "success": False,
            "error": str(e),
            "message": "Coordinator cycle failed",
        }


# ── Singleton Pattern ─────────────────────────────────────────────────

_global_coordinator: BountyCoordinator | None = None
_coordinator_lock = threading.Lock()


def get_bounty_coordinator(config: CoordinatorConfig | None = None) -> BountyCoordinator:
    """Get or create the global bounty coordinator instance."""
    global _global_coordinator
    with _coordinator_lock:
        if _global_coordinator is None:
            _global_coordinator = BountyCoordinator(config)
            logger.info("[BountyCoordinator] Global instance created")
        return _global_coordinator
