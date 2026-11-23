"""Taskmarket Executor — gated write actions for Daydreams TaskMarket.

Wraps ``core.opportunity.agent_market_actions.TaskmarketActions`` behind the
standard executor contract so the execution-queue driver can route
``executor_type="taskmarket"`` items.

Safety model (defense in depth):
  - Mutating actions (``submit_pitch``, ``submit_work``,
    ``request_upload_url``) are listed in ``driver._MUTATING_ACTIONS`` —
    the driver refuses to call them unless ``payload.approved`` is set by
    an explicit human approval (``POST /api/execution-queue/{id}/approve``).
  - ``TaskmarketActions`` additionally requires ``authorized=True`` and
    owner-supplied credentials; this executor never registers identities,
    creates wallets, or signs anything (FINAL_HUMAN_ACTIONS B6/B12).
  - Read actions (``list_pitches``, ``health_check``) need no approval.
"""

from __future__ import annotations

from typing import Any

from core.opportunity.agent_market_actions import TaskmarketActions
from core.opportunity.executors import BaseExecutor, ExecutionResult
from core.security.credential_broker import AccessLevel

_MUTATING = {"submit_pitch", "submit_work", "request_upload_url"}


class TaskmarketExecutor(BaseExecutor):
    """Executor for Taskmarket (api.taskmarket.dev) agent write surface.

    Credentials resolve per action through the project-scoped broker
    (providers ``taskmarket_identity`` / ``taskmarket_api_key``) — nothing
    is cached on the instance and there is no silent global fallback.
    Unscoped config/env secrets require ``allow_unscoped_credentials``.
    """

    platform = "taskmarket"
    credential_sources = {
        "taskmarket_identity": "identity_token",
        "taskmarket_api_key": "api_key",
    }
    credential_env = {
        "taskmarket_identity": "TASKMARKET_IDENTITY_TOKEN",
        "taskmarket_api_key": "TASKMARKET_API_KEY",
    }

    def _credentials(self, level: AccessLevel) -> dict[str, str]:
        creds = {
            "identity_token": self.credential("taskmarket_identity", level),
            "api_key": self.credential("taskmarket_api_key", level),
        }
        return {k: v for k, v in creds.items() if v}

    def _client(self, credentials: dict[str, str], authorized: bool) -> TaskmarketActions:
        return TaskmarketActions(credentials=credentials, authorized=authorized)

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        task_id = str(kwargs.get("task_id", ""))
        try:
            if action == "health_check":
                return await self._health_check()
            if action == "list_pitches":
                client = self._client(self._credentials(AccessLevel.READ_ONLY), authorized=False)
                data = client.list_pitches(task_id)
                client.close()
                return ExecutionResult(True, action, task_id, data=data)
            if action in _MUTATING:
                # Reaching this branch means the queue driver already saw
                # payload.approved (mutating-action gate). TaskmarketActions
                # re-checks authorization + credentials independently.
                credentials = self._credentials(AccessLevel.EXECUTION)
                if not credentials:
                    return ExecutionResult(
                        False,
                        action,
                        task_id,
                        error="no taskmarket credentials — assign to credential broker or enable allow_unscoped_credentials (FINAL_HUMAN_ACTIONS B6)",
                    )
                client = self._client(credentials, authorized=True)
                if action == "submit_pitch":
                    data = client.submit_pitch(task_id, str(kwargs.get("pitch_text", "")))
                elif action == "submit_work":
                    data = client.submit_work(task_id, dict(kwargs.get("payload") or {}))
                else:
                    data = client.request_upload_url(
                        task_id,
                        str(kwargs.get("filename", "submission.md")),
                        str(kwargs.get("content_type", "text/markdown")),
                    )
                client.close()
                return ExecutionResult(True, action, task_id, data=data)
            return ExecutionResult(False, action, task_id, error=f"Unknown action: {action}")
        except Exception as e:
            return ExecutionResult(False, action, task_id, error=str(e))

    async def _health_check(self) -> ExecutionResult:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get("https://api.taskmarket.dev/api/tasks")
            if resp.status_code == 200:
                return ExecutionResult(True, "health_check", self.platform, "taskmarket API reachable")
            return ExecutionResult(False, "health_check", self.platform, error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ExecutionResult(False, "health_check", self.platform, error=str(e))
