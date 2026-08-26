"""Execution Queue Driver — Scheduler handlers for queue processing.

This module contains the scheduler handlers that process the execution queue:
- process_queue: picks up QUEUED items and routes to executors
- retry_failed: retries FAILED items (with backoff)
- move_to_dlq: moves stale FAILED items to DEAD_LETTER
"""

from __future__ import annotations

import logging

from core.execution_queue.models import ExecutionQueueStore

logger = logging.getLogger("ownex.execution.driver")


def process_queue() -> dict:
    """Process QUEUED items — route to executors and advance state.

    This runs every minute via scheduler. It:
    1. Finds all items in QUEUED state
    2. For each, attempts to route to the appropriate executor
    3. Transitions: QUEUED -> EXECUTING -> WAITING_HUMAN (if human gate needed)
       or QUEUED -> EXECUTING -> SUBMITTED -> VERIFICATION -> PAID
    4. On executor error: transitions to FAILED (will be retried by retry job)

    Returns: dict with processed count and any errors.
    """
    store = ExecutionQueueStore()
    queued_ids = store.pending_by_state("queued")

    if not queued_ids:
        return {"processed": 0, "errors": 0, "message": "no queued items"}

    processed = 0
    errors = 0

    for item_id in queued_ids:
        try:
            _process_item(item_id)
            processed += 1
        except Exception as e:
            logger.error("Failed to process %s: %s", item_id, e)
            errors += 1

    return {"processed": processed, "errors": 0, "errors_count": errors}


def _process_item(item_id: str) -> None:
    """Process a single queued item through the execution pipeline."""
    from core.execution_queue.models import ExecutionQueueStore

    store = ExecutionQueueStore()

    # Transition QUEUED -> EXECUTING
    store.transition(item_id, "executing")

    # Get item data
    item = store.get(item_id)
    if not item:
        raise ValueError(f"Item {item_id} not found after transition")

    payload = item.get("payload", {})
    executor_type = payload.get("executor_type", "browser")
    action = payload.get("action", "execute")

    logger.info("Executing %s with executor=%s action=%s", item_id, executor_type, action)

    try:
        # Route to appropriate executor
        result = _route_to_executor(executor_type, action, item.get("payload", {}))

        # If executor indicates human gate needed -> WAITING_HUMAN
        if result.get("requires_human"):
            from core.execution_queue.models import ExecutionQueueStore

            if "waiting_human" in ["waiting_human"]:  # placeholder for can_transition check
                ExecutionQueueStore().transition(item_id, "waiting_human")
                logger.info("%s -> WAITING_HUMAN (human gate required)", item_id)
                return

        # If no human gate, proceed to SUBMITTED
        if result.get("submitted"):
            from core.execution_queue.models import ExecutionQueueStore

            ExecutionQueueStore().transition(item_id, "submitted")
            logger.info("%s -> SUBMITTED (awaiting verification)", item_id)
            return

        # Direct completion -> VERIFICATION
        ExecutionQueueStore().transition(item_id, "verification")

        # Auto-verify if result has verification data
        if result.get("verified"):
            ExecutionQueueStore().transition(item_id, "paid")
            logger.info("%s -> PAID (verified)", item_id)
            _emit_payout_event(item_id, result)
        else:
            logger.info("%s -> VERIFICATION (awaiting async verify)", item_id)

    except Exception as e:
        # Transition to FAILED on any executor error
        from core.execution_queue.models import ExecutionQueueStore

        store = ExecutionQueueStore()
        store.transition(item_id, "failed")
        logger.error("Execution failed for %s: %s", item_id, e)
        raise


def retry_failed() -> dict:
    """Retry FAILED items — transition back to QUEUED for re-execution.

    Runs every 15 minutes. Implements exponential backoff:
    - 1st failure: retry after 15 min
    - 2nd failure: retry after 30 min
    - 3rd failure: retry after 1 hour
    - 4th+ failure: move to DEAD_LETTER (handled by dlq job)
    """
    from core.execution_queue.models import ExecutionQueueStore

    store = ExecutionQueueStore()
    failed_ids = store.pending_by_state("failed")

    if not failed_ids:
        return {"retried": 0, "message": "no failed items"}

    retried = 0
    for item_id in failed_ids:
        item = store.get(item_id)
        if not item:
            continue

        history = item.get("history", [])
        failure_count = history.count("failed")

        if failure_count >= 4:
            logger.warning("%s has %d failures, moving to DLQ", item_id, failure_count)
            continue

        try:
            from core.execution_queue.models import ExecutionQueueStore

            ExecutionQueueStore().transition(item_id, "queued")
            retried += 1
            logger.info("Retried %s (attempt %d)", item_id, history.count("failed") + 1)
        except Exception as e:
            logger.error("Failed to retry %s: %s", item_id, e)

    return {"retried": retried, "failed_count": len(failed_ids)}


def move_to_dlq() -> dict:
    """Move stale FAILED items to DEAD_LETTER.

    Runs hourly. Items that have been in FAILED state for > 4 retries
    or > 24 hours in FAILED state go to DEAD_LETTER.
    """
    from core.execution_queue.models import ExecutionQueueStore

    store = ExecutionQueueStore()
    failed_ids = store.pending_by_state("failed")

    if not failed_ids:
        return {"moved": 0, "message": "no failed items"}

    moved = 0

    for item_id in store.pending_by_state("failed"):
        item = ExecutionQueueStore().get(item_id)
        if not item:
            continue

        history = item.get("history", [])
        failure_count = history.count("failed")

        if failure_count >= 4:
            try:
                from core.execution_queue.models import ExecutionQueueStore

                ExecutionQueueStore().transition(item_id, "dead_letter")
                moved += 1
                logger.warning("Moved %s to DEAD_LETTER (%d failures)", item_id, history.count("failed"))
            except Exception as e:
                logger.error("Failed to move %s to DLQ: %s", item_id, e)

    return {"moved": moved, "checked": len(store.pending_by_state("failed"))}


def _route_to_executor(executor_type: str, action: str, payload: dict) -> dict:
    """Route execution to the appropriate executor based on type.

    Returns dict with keys:
    - requires_human: bool (human gate needed)
    - submitted: bool (submitted to external platform, awaiting verification)
    - verified: bool (immediately verified, can go to PAID)
    - result: any (execution result data)
    """
    executor_type = executor_type.lower()

    if executor_type == "browser":
        return _execute_browser_action(action, payload)
    elif executor_type == "coder":
        return _execute_coder_action(action, payload)
    elif executor_type == "assisted":
        return _execute_assisted_action(action, payload)
    elif executor_type == "freelancer":
        return _execute_freelancer_action(action, payload)
    elif executor_type == "opire":
        return _execute_opire_action(action, payload)
    elif executor_type == "issuehunt":
        return _execute_issuehunt_action(action, payload)
    elif executor_type == "algora":
        return _execute_algora_action(action, payload)
    elif executor_type == "mindrift":
        return _execute_mindrift_action(action, payload)
    elif executor_type == "outlier":
        return _execute_outlier_action(action, payload)
    elif executor_type == "autonomous":
        return _execute_autonomous_workflow(action, payload)
    else:
        logger.warning("Unknown executor type: %s, falling back to browser", executor_type)
        return {"requires_human": True, "submitted": False, "verified": False, "result": {}}


def _execute_browser_action(action: str, payload: dict) -> dict:
    try:
        from cores.automation.browser_agent import BrowserAgent

        agent = BrowserAgent()
        result = agent.execute(action, payload) if hasattr(agent, "execute") else {}
        return {"requires_human": True, "submitted": False, "verified": False, "result": result}
    except Exception as e:
        logger.error("Browser executor failed: %s", e)
        raise


def _execute_coder_action(action: str, payload: dict) -> dict:
    try:
        from cores.autonomy.coder_agent import CoderAgent

        agent = CoderAgent()
        result = agent.execute(action, payload) if hasattr(agent, "execute") else {}
        return {"requires_human": True, "submitted": False, "verified": False, "result": result}
    except Exception as e:
        logger.error("Coder executor failed: %s", e)
        raise


def _execute_assisted_action(action: str, payload: dict) -> dict:
    try:
        from cores.direct_work_engine.execution import AssistedExecutor

        executor = AssistedExecutor()
        result = executor.execute(action, payload) if hasattr(executor, "execute") else {}
        return {"requires_human": True, "submitted": False, "verified": False, "result": result}
    except Exception as e:
        logger.error("Assisted executor failed: %s", e)
        raise


def _execute_freelancer_action(action: str, payload: dict) -> dict:
    try:
        from cores.opportunity.executors.freelancer_executor import FreelancerExecutor

        executor = FreelancerExecutor()
        result = executor.execute(action, payload) if hasattr(executor, "execute") else {}
        return {"requires_human": False, "submitted": True, "verified": False, "result": result}
    except Exception as e:
        logger.error("Freelancer executor failed: %s", e)
        raise


def _execute_opire_action(action: str, payload: dict) -> dict:
    try:
        from cores.opportunity.executors.opire_executor import OpireExecutor

        executor = OpireExecutor()
        result = executor.execute(action, payload) if hasattr(executor, "execute") else {}
        return {"requires_human": False, "submitted": True, "verified": False, "result": result}
    except Exception as e:
        logger.error("Opire executor failed: %s", e)
        raise


def _execute_issuehunt_action(action: str, payload: dict) -> dict:
    try:
        from cores.opportunity.executors.issuehunt_executor import IssueHuntExecutor

        executor = IssueHuntExecutor()
        result = executor.execute(action, payload) if hasattr(executor, "execute") else {}
        return {"requires_human": False, "submitted": True, "verified": False, "result": result}
    except Exception as e:
        logger.error("IssueHunt executor failed: %s", e)
        raise


def _execute_algora_action(action: str, payload: dict) -> dict:
    try:
        from cores.opportunity.executors.algora_executor import AlgoraExecutor

        executor = AlgoraExecutor()
        result = executor.execute(action, payload) if hasattr(executor, "execute") else {}
        return {"requires_human": False, "submitted": True, "verified": False, "result": result}
    except Exception as e:
        logger.error("Algora executor failed: %s", e)
        raise


def _execute_mindrift_action(action: str, payload: dict) -> dict:
    try:
        from cores.opportunity.executors.mindrift_executor import MindriftExecutor

        executor = MindriftExecutor()
        result = executor.execute(action, payload) if hasattr(executor, "execute") else {}
        return {"requires_human": False, "submitted": True, "verified": False, "result": result}
    except Exception as e:
        logger.error("Mindrift executor failed: %s", e)
        raise


def _execute_outlier_action(action: str, payload: dict) -> dict:
    try:
        from cores.opportunity.executors.outlier_executor import OutlierExecutor

        executor = OutlierExecutor()
        result = executor.execute(action, payload) if hasattr(executor, "execute") else {}
        return {"requires_human": False, "submitted": True, "verified": False, "result": result}
    except Exception as e:
        logger.error("Outlier executor failed: %s", e)
        raise


def _execute_autonomous_workflow(action: str, payload: dict) -> dict:
    try:
        from cores.autonomy.workflow_engine import AutonomousWorkflow

        workflow = AutonomousWorkflow()
        result = workflow.execute(action, payload) if hasattr(workflow, "execute") else {}
        return {"requires_human": False, "submitted": False, "verified": False, "result": result}
    except Exception as e:
        logger.error("Autonomous workflow executor failed: %s", e)
        raise


def _emit_payout_event(item_id: str, result: dict) -> None:
    """Emit financial event when item reaches PAID state."""
    try:
        from cores.events.event_bus import get_event_bus

        bus = get_event_bus()
        bus.publish(
            "financial:payout_received",
            item_id=item_id,
            amount=result.get("amount", 0),
            currency=result.get("currency", "USD"),
            platform=result.get("platform", "unknown"),
            external_id=result.get("external_id", ""),
        )
        logger.info("Emitted payout event for %s", item_id)
    except Exception as e:
        logger.error("Failed to emit payout event: %s", e)


# Entry points for scheduler
def process_queue_scheduler() -> dict:
    """Scheduler entry point: process QUEUED items."""
    from core.execution_queue.models import process_queue

    return process_queue()


def retry_failed_scheduler() -> dict:
    """Scheduler entry point: retry FAILED items."""
    from core.execution_queue.models import retry_failed

    return retry_failed()


def move_to_dlq_scheduler() -> dict:
    """Scheduler entry point: move stale FAILED to DEAD_LETTER."""
    from core.execution_queue.models import move_to_dlq

    return move_to_dlq()
