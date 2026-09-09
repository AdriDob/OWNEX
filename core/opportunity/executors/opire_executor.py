"""Opire Executor — Claim bounties, solve, and submit work on Opire.dev / Opyre.com."""

from __future__ import annotations

import os
from typing import Any

import httpx

from core.opportunity.executors import BaseExecutor, ExecutionResult


class OpireExecutor(BaseExecutor):
    """Executor for Opire.dev — claim bounties and submit work."""

    platform = "opire"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.token = self.config.get("token") or os.getenv("OPIRE_TOKEN")
        self.base_url = self.config.get("base_url", "https://api.opire.dev/v1")

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        if action == "claim_bounty":
            return await self.claim_bounty(kwargs.get("bounty_id", ""))
        if action == "submit_work":
            return await self.submit_work(
                kwargs.get("bounty_id", ""),
                kwargs.get("pr_url", ""),
                kwargs.get("description", ""),
            )
        if action == "get_bounties":
            return await self.get_bounties(kwargs.get("status", "open"))
        if action == "get_bounty":
            return await self.get_bounty(kwargs.get("bounty_id", ""))
        if action == "health_check":
            return await self.health_check()
        return ExecutionResult(False, action, "", error=f"Unknown action: {action}")

    async def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def claim_bounty(self, bounty_id: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "claim_bounty", bounty_id, error="OPIRE_TOKEN not configured")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/bounties/{bounty_id}/claim",
                    headers=await self._headers(),
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(True, "claim_bounty", bounty_id, data={"response": data})
                return ExecutionResult(
                    False, "claim_bounty", bounty_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "claim_bounty", bounty_id, error=str(e))

    async def submit_work(self, bounty_id: str, pr_url: str, description: str = "") -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "submit_work", bounty_id, error="OPIRE_TOKEN not configured")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/bounties/{bounty_id}/submit",
                    headers=await self._headers(),
                    json={"pr_url": pr_url, "description": description or "Automated submission via OWNEX CoderAgent"},
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(True, "submit_work", bounty_id, data={"response": data})
                return ExecutionResult(
                    False, "submit_work", bounty_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "submit_work", bounty_id, error=str(e))

    async def get_bounties(self, status: str = "open") -> ExecutionResult:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/bounties",
                    params={"status": status},
                    headers=await self._headers(),
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_bounties", status, data={"bounties": data})
                return ExecutionResult(
                    False, "get_bounties", status, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "get_bounties", status, error=str(e))

    async def get_bounty(self, bounty_id: str) -> ExecutionResult:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/bounties/{bounty_id}",
                    headers=await self._headers(),
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_bounty", bounty_id, data={"bounty": data})
                return ExecutionResult(
                    False, "get_bounty", bounty_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "get_bounty", bounty_id, error=str(e))

    async def health_check(self) -> ExecutionResult:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/health", timeout=15)
                return ExecutionResult(resp.status_code == 200, "health_check", self.base_url)
            except Exception as e:
                return ExecutionResult(False, "health_check", self.base_url, error=str(e))
