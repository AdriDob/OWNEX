"""CoderAgent Autopilot — wires CoderAgent to WorkBank dev bounties for auto-execution.

Pipeline: WorkBank ready_to_deliver (dev_bounty) → CoderAgent.solve_issue() → PR → Human Gate

Only processes bounties under AUTOPILOT_MAX_REWARD to limit risk.
Requires GitHub credentials in IdentityVault.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ownex.coder_autopilot")

AUTOPILOT_MAX_REWARD = 200.0  # Only auto-execute bounties ≤ $200
MAX_PER_RUN = 3  # Limit per scheduler run


def run_coder_autopilot(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Scheduler entry: auto-execute dev bounties via CoderAgent.

    Finds ready_to_deliver dev_bounty items on Opire/Algora platforms,
    sends them to CoderAgent for automated resolution, creates PRs,
    and transitions ExecutionQueue to WAITING_HUMAN for user review.
    """
    results = {"processed": 0, "submitted": 0, "errors": 0, "skipped": 0}

    try:
        from cores.direct_work_engine.workbank import get_workbank

        wb = get_workbank()

        # Filter: dev bounties, ready, public, low reward
        candidates = [
            i
            for i in wb._items.values()
            if i.status == "ready_to_deliver"
            and i.access_status == "public"
            and i.platform in ("opire", "algora", "issuehunt")
            and i.reward <= AUTOPILOT_MAX_REWARD
        ]
        candidates.sort(key=lambda x: -x.reward)
        batch = candidates[:MAX_PER_RUN]

        if not batch:
            return {**results, "message": "no eligible dev bounties"}

        logger.info("CoderAutopilot: processing %d/%d eligible bounties", len(batch), len(candidates))

        for item in batch:
            try:
                result = _solve_one(item)
                results["processed"] += 1
                if result.get("success"):
                    results["submitted"] += 1
                else:
                    results["skipped"] += 1
            except Exception as e:
                logger.error("CoderAutopilot error on %s: %s", item.id, e)
                results["errors"] += 1

    except Exception as e:
        logger.error("CoderAutopilot failed: %s", e)
        results["errors"] += 1

    return results


def _solve_one(item) -> dict[str, Any]:
    """Send one bounty to CoderAgent and track in ExecutionQueue."""
    import asyncio

    from core.execution_queue.models import ExecState, ExecutionQueueStore

    eq = ExecutionQueueStore()
    eq.add(item.id, {"title": item.title, "reward": item.reward, "platform": item.platform})
    eq.transition(item.id, ExecState.QUEUED)
    eq.transition(item.id, ExecState.EXECUTING)

    try:
        from cores.autonomy.coder_agent import CoderAgent

        agent = CoderAgent()
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    agent.solve_issue(
                        issue_url=item.url or "",
                        platform=item.platform,
                    ),
                )
                result = future.result(timeout=600)  # 10 min timeout
        else:
            result = loop.run_until_complete(
                agent.solve_issue(
                    issue_url=item.url or "",
                    platform=item.platform,
                )
            )

        if result.success and result.pr_result:
            eq.transition(item.id, ExecState.WAITING_HUMAN)
            logger.info("CoderAutopilot: PR created for %s — waiting for human merge", item.id)
            return {"success": True, "pr_url": getattr(result.pr_result, "url", "")}
        else:
            eq.transition(item.id, ExecState.FAILED)
            return {"success": False, "reason": "coder agent could not solve"}

    except Exception as e:
        logger.error("CoderAutopilot solve failed for %s: %s", item.id, e)
        eq.transition(item.id, ExecState.FAILED)
        raise
