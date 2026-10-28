"""Mindrift Executor — Claim tasks, solve, and submit work on Mindrift.io.

Automation policy (vNext §1): Mindrift's ToS stance on bots is UNVERIFIED,
so this module defaults to RESTRICTED: it may READ (list/health) but never
auto-claim without explicit human opt-in. Claiming a specific task the human
approved always works. Claiming "whatever is open" requires
``allow_auto=True`` or env ``MINDRIFT_AUTOCLAIM=1``.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

from cores.opportunity.executors import BaseExecutor, ExecutionResult

LOG = logging.getLogger("ownex.mindrift")

# Automation levels per surface (vNext §1). Only READ is allowed by default.
WATCH_LEVELS: dict[str, str] = {
    "list_tasks": "ALLOWED",  # read-only listing
    "claim_specific": "ALLOWED",  # explicit task_id approved by a human
    "claim_first_open": "RESTRICTED",  # needs allow_auto=True or MINDRIFT_AUTOCLAIM=1
    "auto_submit": "RESTRICTED",  # solution posts go through Human Gate
}

AUTOCLAIM_ENV = "MINDRIFT_AUTOCLAIM"
SEEN_FILENAME = "mindrift_seen_tasks.json"
MAX_SEEN_KEPT = 500


class MindriftExecutor(BaseExecutor):
    """Executor for Mindrift.io — claim AI data tasks and submit solutions."""

    platform = "mindrift"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.token = self.config.get("token") or os.getenv("MINDRIFT_EMAIL")
        self.base_url = self.config.get("base_url", "https://api.mindrift.io/v1")

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        if action == "claim_task":
            return await self.claim_task(kwargs.get("task_id", ""))
        if action == "submit_task":
            return await self.submit_task(
                kwargs.get("task_id", ""),
                kwargs.get("solution_url", ""),
                kwargs.get("description", ""),
            )
        if action == "get_tasks":
            return await self.get_tasks(kwargs.get("status", "open"))
        if action == "health_check":
            return await self.health_check()
        return ExecutionResult(False, action, "", error=f"Unknown action: {action}")

    async def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def claim_task(self, task_id: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "claim_task", task_id, error="MINDRIFT_EMAIL not configured")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/tasks/{task_id}/claim",
                    headers=await self._headers(),
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(True, "claim_task", task_id, data={"response": data})
                return ExecutionResult(
                    False, "claim_task", task_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "claim_task", task_id, error=str(e))

    async def submit_task(self, task_id: str, solution_url: str, description: str = "") -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "submit_task", task_id, error="MINDRIFT_EMAIL not configured")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/tasks/{task_id}/submit",
                    headers=await self._headers(),
                    json={
                        "solution_url": solution_url,
                        "description": description or "Automated submission via OWNEX CoderAgent",
                    },
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(True, "submit_task", task_id, data={"response": data})
                return ExecutionResult(
                    False, "submit_task", task_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "submit_task", task_id, error=str(e))

    async def get_tasks(self, status: str = "open") -> ExecutionResult:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/tasks",
                    params={"status": status},
                    headers=await self._headers(),
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_tasks", status, data={"tasks": data})
                return ExecutionResult(False, "get_tasks", status, error=f"HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                return ExecutionResult(False, "get_tasks", status, error=str(e))

    async def health_check(self) -> ExecutionResult:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/health", timeout=15)
                return ExecutionResult(resp.status_code == 200, "health_check", self.base_url)
            except Exception as e:
                return ExecutionResult(False, "health_check", self.base_url, error=str(e))


async def claim(task_id: str | None = None, *, allow_auto: bool = False) -> ExecutionResult:
    """Top-level claim function for scheduler handler.

    References: ``core.opportunity.executors.mindrift_executor:claim``

    - Explicit ``task_id`` (human-approved): always attempted.
    - No ``task_id`` ("first open"): RESTRICTED — requires ``allow_auto=True``
      or env ``MINDRIFT_AUTOCLAIM=1``. Otherwise it REFUSES with instructions
      instead of claiming blindly (UNKNOWN → NO AUTO-ACTION).
    """
    executor = MindriftExecutor()
    if task_id:
        return await executor.claim_task(task_id)
    if not allow_auto and os.getenv(AUTOCLAIM_ENV, "") != "1":
        return ExecutionResult(
            False,
            "claim",
            task_id,
            error="auto-claim disabled: pass a human-approved task_id (or set MINDRIFT_AUTOCLAIM=1). "
            "Use watch_new_tasks() to review open tasks first.",
        )
    # Find first available task and claim it (explicit opt-in only)
    tasks_result = await executor.get_tasks("open")
    if not tasks_result.success or not tasks_result.data:
        return ExecutionResult(False, "claim", task_id, error="No open tasks available")
    tasks = tasks_result.data.get("tasks", [])
    if not tasks:
        return ExecutionResult(False, "claim", task_id, error="No open tasks available")
    first_task_id = tasks[0].get("id") if isinstance(tasks[0], dict) and "id" in tasks[0] else str(tasks[0])
    return await executor.claim_task(first_task_id)


def _seen_path(store_path: str | Path | None = None) -> Path:
    if store_path:
        return Path(store_path)
    base = os.environ.get("OWNEX_DATA_DIR", "data")
    return Path(base) / SEEN_FILENAME


async def watch_new_tasks(
    store_path: str | Path | None = None,
    executor: Any = None,
) -> dict[str, Any]:
    """Read-only watch: list open tasks, report only the unseen ones.

    NEVER claims, NEVER submits. Persists seen ids (cap 500). Without a
    token it reports ``configured: False`` instead of failing silently.
    Executor injectable for offline tests.
    """
    path = _seen_path(store_path)
    seen: set[str] = set()
    try:
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                seen = {str(x) for x in raw}
    except (OSError, ValueError) as exc:
        LOG.warning("mindrift watch: seen store ilegible, se empieza vacío: %s", exc)
    exe = executor or MindriftExecutor()
    if not exe.token:
        return {
            "configured": False,
            "open": 0,
            "new_tasks": [],
            "note": "Set MINDRIFT_EMAIL (or vault token) to enable watching.",
        }
    try:
        result = await exe.get_tasks("open")
    except Exception as exc:
        return {"configured": True, "open": 0, "new_tasks": [], "error": f"list failed: {exc}"}
    if not result.success or not result.data:
        return {"configured": True, "open": 0, "new_tasks": [], "error": result.error or "empty response"}
    tasks = result.data.get("tasks", []) if isinstance(result.data, dict) else []
    if not isinstance(tasks, list):
        tasks = []
    open_count = len(tasks)
    fresh: list[dict[str, Any]] = []
    for t in tasks:
        tid = str(t.get("id", t) if isinstance(t, dict) else t)
        if tid and tid not in seen:
            fresh.append(
                {
                    "id": tid,
                    "title": t.get("title", "") if isinstance(t, dict) else "",
                    "reward": t.get("reward") if isinstance(t, dict) else None,
                }
            )
            seen.add(tid)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        kept = sorted(seen)[-MAX_SEEN_KEPT:]
        path.write_text(json.dumps(kept, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return {"configured": True, "open": open_count, "new_tasks": fresh}
