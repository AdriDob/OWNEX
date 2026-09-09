"""Immunefi Executor — Submit reports, claim bounties on Immunefi."""

from __future__ import annotations

import os
from typing import Any

import httpx

from core.opportunity.executors import BaseExecutor, ExecutionResult


class ImmunefiExecutor(BaseExecutor):
    """Executor for Immunefi — submit reports, claim bounties."""

    platform = "immunefi"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.token = self.config.get("token") or os.getenv("IMMUNEFI_API_KEY")
        self.base_url = self.config.get("base_url", "https://api.immunefi.com")

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
            return await self.claim_bounty(kwargs.get("report_id") or "")
        if action == "get_report":
            return await self.get_report(kwargs.get("report_id") or "")
        if action == "get_program":
            return await self.get_program(kwargs.get("program_id") or "")
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
        program_id: str,
        title: str,
        vulnerability_type: str,
        severity: str,
        description: str,
        impact: str = "",
        steps_to_reproduce: str = "",
        poc: str = "",
        attachments: list[str] | None = None,
    ) -> ExecutionResult:
        """Submit a vulnerability report to Immunefi."""
        if not self.token:
            return ExecutionResult(False, "submit_report", "", error="IMMUNEFI_API_KEY not configured")

        if not program_id:
            return ExecutionResult(False, "submit_report", "", error="Program ID required")

        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "program_id": program_id,
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
                        f"{self.base_url}/reports",
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
                            f"Report submitted to program {program_id}",
                            data={"report_id": data.get("id"), "url": data.get("url")},
                        )
                    return ExecutionResult(
                        False, "submit_report", "", error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                    )
            except Exception as e:
                return ExecutionResult(False, "submit_report", "", error=str(e))

    async def claim_bounty(self, report_id: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "claim_bounty", report_id, error="IMMUNEFI_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/reports/{report_id}/claim",
                    headers=await self._headers(),
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(True, "claim_bounty", report_id, data={"response": data})
                return ExecutionResult(
                    False, "claim_bounty", report_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "claim_bounty", report_id, error=str(e))

    async def get_report(self, report_id: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "get_report", "", error="IMMUNEFI_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/reports/{report_id}",
                    headers=await self._headers(),
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_report", report_id, data={"report": data})
                return ExecutionResult(
                    False, "get_report", report_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "get_report", "", error=str(e))

    async def get_program(self, program_id: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "get_program", program_id, error="IMMUNEFI_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/programs/{program_id}",
                    headers=await self._headers(),
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_program", program_id, data=data)
                return ExecutionResult(
                    False, "get_program", program_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "get_program", program_id, error=str(e))

    async def health_check(self) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "health_check", self.base_url, error="IMMUNEFI_API_KEY not configured")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/health", timeout=15)
                return ExecutionResult(resp.status_code == 200, "health_check", self.base_url)
            except Exception as e:
                return ExecutionResult(False, "health_check", self.base_url, error=str(e))
