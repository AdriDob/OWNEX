"""Synack Executor — Submit reports, claim bounties on Synack."""

from __future__ import annotations

import os
from typing import Any

import httpx

from core.opportunity.executors import BaseExecutor, ExecutionResult


class SynackExecutor(BaseExecutor):
    """Executor for Synack — submit reports, claim bounties."""

    platform = "synack"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.token = self.config.get("token") or os.getenv("SYNACK_API_KEY")
        self.base_url = self.config.get("base_url", "https://platform.synack.com/api")

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        if action == "submit_report":
            return await self.submit_report(
                kwargs.get("program_id") or "",
                kwargs.get("title") or "",
                kwargs.get("vulnerability_type") or "",
                kwargs.get("severity") or "",
                kwargs.get("description") or "",
                kwargs.get("impact") or "",
                kwargs.get("steps_to_reproduce") or "",
                kwargs.get("poc") or "",
                kwargs.get("attachments"),
            )
        if action == "claim_bounty":
            return await self.claim_bounty(kwargs.get("vulnerability_id") or "")
        if action == "get_vulnerability":
            return await self.get_vulnerability(kwargs.get("vulnerability_id") or "")
        if action == "get_mission":
            return await self.get_mission(kwargs.get("mission_id") or "")
        if action == "health_check":
            return await self.health_check()
        return ExecutionResult(False, action, "", error=f"Unknown action: {action}")

    async def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def submit_report(
        self,
        mission_id: str,
        title: str,
        vulnerability_type: str,
        severity: str,
        description: str,
        impact: str = "",
        steps_to_reproduce: str = "",
        poc: str = "",
        attachments: list[str] | None = None,
    ) -> ExecutionResult:
        """Submit a vulnerability report to Synack."""
        if not self.token:
            return ExecutionResult(False, "submit_report", "", error="SYNACK_API_KEY not configured")

        if not mission_id:
            return ExecutionResult(False, "submit_report", "", error="Mission ID required")

        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "mission_id": mission_id,
                    "title": title,
                    "vulnerability_type": vulnerability_type,
                    "severity": severity,
                    "description": description,
                    "impact": impact,
                    "steps_to_reproduce": steps_to_reproduce,
                    "poc": poc,
                    "attachments": attachments or [],
                }

                headers = await self._headers()
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{self.base_url}/vulnerabilities",
                        headers=headers,
                        json=payload,
                        timeout=30,
                    )

                    if resp.status_code in (200, 201):
                        data = resp.json()
                        return ExecutionResult(
                            True,
                            "submit_report",
                            "",
                            f"Vulnerability submitted to mission {mission_id}",
                            data={"vulnerability_id": data.get("id"), "url": data.get("url")},
                        )
                    return ExecutionResult(
                        False, "submit_report", "", error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                    )
            except Exception as e:
                return ExecutionResult(False, "submit_report", "", error=str(e))

    async def claim_bounty(self, vulnerability_id: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "claim_bounty", vulnerability_id, error="SYNACK_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/vulnerabilities/{vulnerability_id}/claim",
                    headers=await self._headers(),
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(True, "claim_bounty", vulnerability_id, data={"response": data})
                return ExecutionResult(
                    False, "claim_bounty", vulnerability_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "claim_bounty", vulnerability_id, error=str(e))

    async def get_vulnerability(self, vulnerability_id: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "get_vulnerability", "", error="SYNACK_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/vulnerabilities/{vulnerability_id}",
                    headers=await self._headers(),
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_vulnerability", vulnerability_id, data={"vulnerability": data})
                return ExecutionResult(
                    False, "get_vulnerability", vulnerability_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "get_vulnerability", "", error=str(e))

    async def get_mission(self, mission_id: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "get_mission", mission_id, error="SYNACK_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/missions/{mission_id}",
                    headers=await self._headers(),
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_mission", mission_id, data=data)
                return ExecutionResult(
                    False, "get_mission", mission_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "get_mission", mission_id, error=str(e))

    async def health_check(self) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "health_check", self.base_url, error="SYNACK_API_KEY not configured")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/health", timeout=15)
                return ExecutionResult(resp.status_code == 200, "health_check", self.base_url)
            except Exception as e:
                return ExecutionResult(False, "health_check", self.base_url, error=str(e))
