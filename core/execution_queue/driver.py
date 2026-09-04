"""Execution Queue Driver — connects state machine to actual executors."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

from core.execution_queue.models import (
    ExecState,
    ExecutionQueueStore,
)

logger = logging.getLogger("ownex.execution_queue.driver")

# Import executors
try:
    from core.opportunity.executors.algora_executor import AlgoraExecutor
    from core.opportunity.executors.bugcrowd_executor import BugcrowdExecutor
    from core.opportunity.executors.freelancer_executor import FreelancerExecutor

    # Security bounty executors
    from core.opportunity.executors.hackerone_executor import HackerOneExecutor
    from core.opportunity.executors.immunefi_executor import ImmunefiExecutor
    from core.opportunity.executors.intigriti_executor import IntigritiExecutor
    from core.opportunity.executors.issuehunt_executor import IssueHuntExecutor
    from core.opportunity.executors.mindrift_executor import MindriftExecutor
    from core.opportunity.executors.opire_executor import OpireExecutor
    from core.opportunity.executors.outlier_executor import OutlierExecutor
    from core.opportunity.executors.synack_executor import SynackExecutor
    from core.opportunity.executors.yeswehack_executor import YesWeHackExecutor
except ImportError as e:
    logger.warning(f"Some executors not available: {e}")

# Import assisted mode for human-in-the-loop
try:
    from core.opportunity.executors.assisted_mode import AssistedExecutor, PreparedWork
    from core.opportunity.guides.platform_guides import get_platform_guide
except ImportError:
    AssistedExecutor = None
    PreparedWork = None
    get_platform_guide = None

# Import trust engine for auto-approval
try:
    from core.trust_engine import get_trust_engine
except ImportError:
    get_trust_engine = None

# Import execution-revenue sync
try:
    from cores.financial.execution_sync import get_execution_revenue_sync
except ImportError:
    get_execution_revenue_sync = None


@dataclass
class ExecutionResult:
    success: bool
    message: str
    data: dict | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExecutionQueueDriver:
    """Drives the execution queue by processing items through their lifecycle."""

    def __init__(self, store: ExecutionQueueStore | None = None):
        # Initialize execution-revenue sync
        if get_execution_revenue_sync:
            sync = get_execution_revenue_sync()
            sync.initialize()
            self.store = store or ExecutionQueueStore(on_transition=self._on_store_transition)
        else:
            self.store = store or ExecutionQueueStore()
        self._executors = self._init_executors()
        self._running = False
        self._retry_counts: dict[str, int] = {}
        self._max_retries = 3

    def _on_store_transition(self, item_id: str, old_state: str, new_state: str, payload: dict) -> None:
        """Callback for store transitions - emits event for execution-revenue sync."""
        from cores.events.event_bus import get_event_bus

        bus = get_event_bus()
        bus.publish(
            "execution:state_changed",
            item_id=item_id,
            old_state=old_state,
            new_state=new_state,
            payload=payload,
        )

    def _init_executors(self) -> dict[str, Any]:
        """Initialize platform-specific executors."""
        executors = {}
        try:
            executors["algora"] = AlgoraExecutor()
        except Exception:
            pass
        try:
            executors["opire"] = OpireExecutor()
        except Exception:
            pass
        try:
            executors["freelancer"] = FreelancerExecutor()
        except Exception:
            pass
        try:
            executors["issuehunt"] = IssueHuntExecutor()
        except Exception:
            pass
        try:
            executors["mindrift"] = MindriftExecutor()
        except Exception:
            pass
        try:
            executors["outlier"] = OutlierExecutor()
        except Exception:
            pass
        try:
            executors["issuehunt"] = IssueHuntExecutor()
        except Exception:
            pass
        # Security bounty executors
        try:
            executors["hackerone"] = HackerOneExecutor()
        except Exception:
            pass
        try:
            executors["bugcrowd"] = BugcrowdExecutor()
        except Exception:
            pass
        try:
            executors["intigriti"] = IntigritiExecutor()
        except Exception:
            pass
        try:
            executors["yeswehack"] = YesWeHackExecutor()
        except Exception:
            pass
        try:
            executors["immunefi"] = ImmunefiExecutor()
        except Exception:
            pass
        try:
            executors["synack"] = SynackExecutor()
        except Exception:
            pass
        return executors

    def _get_executor(self, platform: str) -> Any | None:
        """Get executor for platform."""
        platform_lower = platform.lower()
        if platform_lower in self._executors:
            return self._executors[platform_lower]
        # Try case-insensitive
        for k, v in self._executors.items():
            if k.lower() == platform_lower:
                return v
        return None

    async def process_queue_scheduler(self) -> dict[str, Any]:
        """Scheduler job: process all QUEUED items."""
        results = {"processed": 0, "succeeded": 0, "failed": 0, "waiting_human": 0}

        queued_items = self.store.pending_by_state(ExecState.QUEUED.value)

        for item_id in queued_items:
            try:
                result = await self.process_item(item_id)
                if result.success:
                    results["succeeded"] += 1
                else:
                    results["failed"] += 1
                results["processed"] += 1
            except Exception as e:
                logger.error(f"Error processing {item_id}: {e}")
                results["failed"] += 1
                results["processed"] += 1

                # Transition to FAILED
                try:
                    self.store.transition(item_id, ExecState.FAILED)
                except Exception:
                    pass

        return results

    async def process_item(self, item_id: str) -> ExecutionResult:
        """Process a single queued item through its execution lifecycle."""
        item = self.store.get(item_id)
        if not item:
            return ExecutionResult(False, f"Item {item_id} not found")

        if item["state"] != ExecState.QUEUED.value:
            return ExecutionResult(False, f"Item {item_id} not in QUEUED state")

        payload = item.get("payload", {})
        platform = payload.get("platform", "").lower()
        opportunity_id = payload.get("id", item_id)

        logger.info(f"[EXECUTION] Processing {item_id} for platform {platform}")

        # Transition to EXECUTING
        self.store.transition(item_id, ExecState.EXECUTING)

        try:
            # Get executor for platform
            executor = self._get_executor(payload.get("platform", ""))

            if not executor:
                # No specific executor - use assisted mode
                return await self._execute_assisted(item_id, payload)

            # Execute via platform-specific executor
            return await self._execute_via_executor(item_id, payload, executor)

        except Exception as e:
            logger.error(f"Execution error for {item_id}: {e}")
            # Transition to FAILED
            self.store.transition(item_id, ExecState.FAILED)
            return ExecutionResult(False, f"Execution failed: {e}")

    async def _execute_via_executor(self, item_id: str, payload: dict, executor: Any) -> ExecutionResult:
        """Execute via platform-specific executor."""
        try:
            # Determine action from payload
            action = payload.get("action", "claim")

            if hasattr(executor, "execute"):
                result = await executor.execute(action=action, **payload)
            else:
                # Try claim_bounty for bounty platforms
                result = await executor.claim_bounty(payload.get("id", ""))

            if result.success:
                # Transition to SUBMITTED
                self.store.transition(item_id, ExecState.SUBMITTED)
                return ExecutionResult(True, "Submitted successfully", result.data)
            else:
                # Transition to FAILED
                self.store.transition(item_id, ExecState.FAILED)
                return ExecutionResult(False, result.error or "Submission failed")

        except Exception as e:
            logger.error(f"Executor error: {e}")
            # Transition to FAILED
            self.store.transition(item_id, ExecState.FAILED)
            return ExecutionResult(False, f"Executor error: {e}")

    async def _execute_assisted(self, item_id: str, payload: dict) -> ExecutionResult:
        """Execute via assisted mode (human-in-the-loop)."""
        if AssistedExecutor is None or PreparedWork is None:
            self.store.transition(item_id, ExecState.FAILED)
            return ExecutionResult(False, "Assisted mode not available")

        try:
            # Create assisted executor (no base executor needed for preparation)
            assisted = AssistedExecutor(base_executor=None)

            # Prepare work
            opportunity = {
                "id": payload.get("id", ""),
                "platform": payload.get("platform", ""),
                "title": payload.get("title", ""),
                "description": payload.get("description", ""),
                "url": payload.get("url", ""),
                "reward": payload.get("reward", 0),
                "metadata": payload.get("metadata", {}),
            }

            prepared = await assisted.prepare_work(opportunity)

            # Save to disk
            work_dir = await assisted.save_work_to_disk(prepared)

            # Check if auto-approval is possible via trust engine
            if get_trust_engine:
                trust_engine = get_trust_engine()
                platform = payload.get("platform", "")
                reward = payload.get("reward", 0)
                can_approve, reason = trust_engine.can_auto_approve(
                    str(payload.get("platform", "")), float(payload.get("reward", 0))
                )

                if can_approve:
                    # Auto-submit using the prepared work
                    assisted_executor = AssistedExecutor(base_executor=None)
                    result = await assisted_executor.auto_submit(prepared)

                    if result.get("success"):
                        self.store.transition(item_id, ExecState.SUBMITTED)
                        return ExecutionResult(True, "Auto-submitted via trust engine", result)

            # Not auto-approved - move to WAITING_HUMAN
            self.store.transition(item_id, ExecState.WAITING_HUMAN)

            # Prepare work for human review
            if AssistedExecutor:
                assisted_executor = AssistedExecutor(base_executor=None)
                await assisted_executor.save_work_to_disk(prepared)

            return ExecutionResult(
                True,
                "Prepared for human review - awaiting approval",
                {"status": "waiting_human", "requires_approval": True},
            )

        except Exception as e:
            logger.error(f"Assisted execution error: {e}")
            self.store.transition(item_id, ExecState.FAILED)
            return ExecutionResult(False, f"Assisted execution failed: {e}")

    async def retry_failed_scheduler(self) -> dict[str, Any]:
        """Scheduler job: retry FAILED items (up to max retries)."""
        results = {"retried": 0, "skipped": 0}

        failed_items = self.store.pending_by_state(ExecState.FAILED.value)

        for item_id in failed_items:
            item = self.store.get(item_id)
            if not item:
                results["skipped"] += 1
                continue

            # Check retry count
            retry_count = self._retry_counts.get(item_id, 0)
            if retry_count >= self._max_retries:
                logger.warning(f"Max retries exceeded for {item_id}, moving to DEAD_LETTER")
                self.store.transition(item_id, ExecState.DEAD_LETTER)
                results["skipped"] += 1
                continue

            # Increment retry count
            self._retry_counts[item_id] = retry_count + 1

            # Reset to QUEUED for retry
            self.store.transition(item_id, ExecState.QUEUED)
            results["retried"] += 1

            logger.info(f"Retrying item {item_id} (attempt {retry_count + 1})")

        return results

    async def move_to_dlq_scheduler(self) -> dict[str, Any]:
        """Scheduler job: move stale FAILED items to DEAD_LETTER."""
        results = {"moved": 0}

        failed_items = self.store.pending_by_state(ExecState.FAILED.value)

        for item_id in failed_items:
            item = self.store.get(item_id)
            if not item:
                continue

            retry_count = self._retry_counts.get(item_id, 0)
            if retry_count >= self._max_retries:
                self.store.transition(item_id, ExecState.DEAD_LETTER)
                results["moved"] += 1
                logger.info(f"Moved {item_id} to DEAD_LETTER after {retry_count} retries")

        return results

    async def process_waiting_human(self, item_id: str, approved: bool) -> ExecutionResult:
        """Process human approval for WAITING_HUMAN item."""
        item = self.store.get(item_id)
        if not item:
            return ExecutionResult(False, f"Item {item_id} not found")

        if item["state"] != ExecState.WAITING_HUMAN.value:
            return ExecutionResult(False, f"Item {item_id} not in WAITING_HUMAN state")

        if approved:
            # Transition to SUBMITTED
            self.store.transition(item_id, ExecState.SUBMITTED)
            return ExecutionResult(True, "Approved by human - ready for submission")
        else:
            # Transition to REJECTED
            self.store.transition(item_id, ExecState.REJECTED)
            return ExecutionResult(False, "Rejected by human")


# Singleton instance
_execution_driver: Any | None = None


def get_execution_driver() -> ExecutionQueueDriver:
    """Get or create the singleton execution driver."""
    global _execution_driver
    if _execution_driver is None:
        _execution_driver = ExecutionQueueDriver()
    return _execution_driver


async def process_queue_scheduler() -> dict[str, Any]:
    """Scheduler job: process QUEUED items."""
    driver = get_execution_driver()
    return await driver.process_queue_scheduler()


async def retry_failed_scheduler() -> dict[str, Any]:
    """Scheduler job: retry FAILED items."""
    driver = get_execution_driver()
    return await driver.retry_failed_scheduler()


async def move_to_dlq_scheduler() -> dict[str, Any]:
    """Scheduler job: move stale FAILED to DEAD_LETTER."""
    driver = get_execution_driver()
    return await driver.move_to_dlq_scheduler()


async def process_waiting_human(item_id: str, approved: bool) -> dict[str, Any]:
    """Process human approval for WAITING_HUMAN item."""
    driver = get_execution_driver()
    result = await driver.process_waiting_human(item_id, approved)
    return (
        result.to_dict()
        if hasattr(result, "to_dict")
        else {
            "success": result.success,
            "message": result.message,
            "data": result.data,
            "error": result.error,
        }
    )
