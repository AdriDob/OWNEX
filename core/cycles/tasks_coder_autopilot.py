"""CoderAgent Autopilot — wires CoderAgent to WorkBank dev bounties.

Pipeline: WorkBank ready_to_deliver (dev_bounty) → CoderAgent.solve_issue()
→ local delivery package → WAITING_HUMAN (owner review).

The autonomous stage NEVER creates a PR, claims a bounty or submits work.
External publication only happens via CoderAgent.publish_delivery() after
explicit owner approval.

Queue rules (B1): the ExecutionQueue record is never overwritten; items are
advanced through the canonical TRANSITIONS graph via find_path(); re-runs
are idempotent (in-flight/review states are skipped).

Repository rules (B2): repo_url is derived ONLY from a GitHub issue/PR URL
found in the item. Anything else blocks safely — never guess.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("ownex.coder_autopilot")

AUTOPILOT_MAX_REWARD = 200.0  # Only auto-execute bounties ≤ $200
MAX_PER_RUN = 3  # Limit per scheduler run

_GITHUB_ISSUE_RE = re.compile(r"github\.com/([^/]+/[^/]+)/(?:issues|pull)/(\d+)", re.I)

# States where the item is already in flight or past the autonomous stage —
# a scheduler re-run must not touch them (idempotency).
_IN_FLIGHT_STATES = {"queued", "executing", "waiting_human", "submitted", "verification", "paid"}


def run_coder_autopilot(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Scheduler entry: auto-execute dev bounties via CoderAgent.

    Finds ready_to_deliver dev_bounty items on Opire/Algora platforms,
    sends them to CoderAgent for automated resolution, builds a local
    delivery package and parks the queue item in WAITING_HUMAN/BLOCKED.
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


def _extract_github_target(url: str) -> tuple[str, str] | None:
    """Return (repo_slug, issue_number) for a GitHub issue/PR URL, else None."""
    m = _GITHUB_ISSUE_RE.search(url or "")
    if not m:
        return None
    return m.group(1), m.group(2)


def _advance(store: Any, item_id: str, target: str) -> bool:
    """Walk the legal TRANSITIONS path to ``target``. False if unreachable."""
    from core.execution_queue.models import ExecState, find_path

    rec = store.get(item_id)
    if rec is None:
        return False
    path = find_path(ExecState(rec["state"]), ExecState(target))
    if path is None:
        return False
    for state in path:
        store.transition(item_id, state)
    return True


def _block_item(store: Any, item_id: str) -> None:
    """Park an item as BLOCKED via the only legal route (…→waiting_human→blocked)."""
    _advance(store, item_id, "waiting_human")
    _advance(store, item_id, "blocked")


def _solve_one(item) -> dict[str, Any]:
    """Send one bounty to CoderAgent and track in ExecutionQueue."""
    import asyncio

    from core.execution_queue.models import ExecutionQueueStore

    eq = ExecutionQueueStore()

    # B1: never overwrite an existing mirrored record — create only if absent.
    if eq.get(item.id) is None:
        eq.add(
            item.id,
            {
                "title": item.title,
                "reward": item.reward,
                "platform": item.platform,
                "url": item.url,
                "description": item.description,
                "executor_type": "coder",
                "action": "solve_issue",
                "source": "coder_autopilot",
            },
        )

    rec = eq.get(item.id)
    state = rec["state"] if rec else "discovered"
    if state in _IN_FLIGHT_STATES or state in ("rejected", "blocked", "dead_letter"):
        return {"success": False, "reason": f"item already {state}", "skipped": True}

    # Legal path to EXECUTING (e.g. discovered→qualified→ready→queued→executing)
    if not _advance(eq, item.id, "executing"):
        logger.warning("CoderAutopilot: no legal path to executing for %s (state=%s)", item.id, state)
        return {"success": False, "reason": "no legal queue transition"}

    # B2: resolve the exact repo+issue; block safely when not derivable.
    target = _extract_github_target(item.url)
    if target is None:
        logger.info("CoderAutopilot: %s has no resolvable GitHub issue URL (%s) — blocking", item.id, item.url)
        _block_item(eq, item.id)
        eq.update_payload(item.id, blocked_reason="no_resolvable_repository_url")
        return {"success": False, "reason": "no_resolvable_repository_url", "blocked": True}

    repo_slug, issue_number = target
    repo_url = f"https://github.com/{repo_slug}"
    issue_data = {
        "id": item.id,
        "number": int(issue_number),
        "title": item.title,
        "body": item.description or "",
        "url": item.url,
        "platform": item.platform,
    }

    try:
        from core.autonomy.coder_agent import CoderAgent

        agent = CoderAgent()
        coro = agent.solve_issue(issue_data=issue_data, repo_url=repo_url, platform=item.platform)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            result = asyncio.run(coro)
        else:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                result = future.result(timeout=900)  # 15 min: clone+gen+tests

        verdict = getattr(result, "verdict", None)
        payload_update = {
            "verdict": verdict,
            "workspace_path": getattr(result, "workspace_path", None),
            "patch_path": getattr(result, "patch_path", None),
            "delivery_package": getattr(result, "delivery_package", None),
            "error": getattr(result, "error", None),
        }
        eq.update_payload(item.id, **{k: v for k, v in payload_update.items() if v is not None})

        if verdict == "ready_for_owner_review":
            # Local package validated; external publish needs owner approval.
            _advance(eq, item.id, "waiting_human")
            logger.info("CoderAutopilot: delivery package ready for %s — waiting for owner", item.id)
            return {"success": True, "delivery_package": getattr(result, "delivery_package", "")}
        if verdict == "blocked":
            _block_item(eq, item.id)
            return {"success": False, "reason": getattr(result, "error", "blocked"), "blocked": True}

        _advance(eq, item.id, "failed")
        return {"success": False, "reason": getattr(result, "error", None) or f"verdict={verdict}"}

    except Exception as e:
        logger.error("CoderAutopilot solve failed for %s: %s", item.id, e)
        _advance(eq, item.id, "waiting_human")
        _advance(eq, item.id, "failed")
        raise
