"""HackerOne Executor — Submit reports, claim bounties on HackerOne."""

from __future__ import annotations

import os
from typing import Any

import httpx

from core.opportunity.executors import BaseExecutor, ExecutionResult


class HackerOneExecutor(BaseExecutor):
    """Executor for HackerOne — submit reports, claim bounties."""

    platform = "hackerone"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.token = self.config.get("token") or os.getenv("HACKERONE_API_KEY")
        self.handle = self.config.get("handle", "")
        self.base_url = self.config.get("base_url", "https://api.hackerone.com/v1")

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        if action == "submit_report":
            return await self.submit_report(
                kwargs.get("program_handle") or "",
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
            return await self.get_program(kwargs.get("program_handle") or "")
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
        program_handle: str,
        title: str,
        vulnerability_type: str,
        severity: str,
        description: str,
        impact: str = "",
        steps_to_reproduce: str = "",
        poc: str = "",
        attachments: list[str] | None = None,
    ) -> ExecutionResult:
        """Submit a vulnerability report to HackerOne."""
        if not self.token:
            return ExecutionResult(False, "submit_report", "", error="HACKERONE_API_KEY not configured")

        if not program_handle:
            return ExecutionResult(False, "submit_report", "", error="Program handle required")

        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "data": {
                        "type": "report",
                        "attributes": {
                            "title": title,
                            "vulnerability_information": description,
                            "impact": impact,
                            "steps_to_reproduce": steps_to_reproduce,
                            "poc": poc,
                            "severity": severity,
                            "weakness": vulnerability_type,
                            "attachments": attachments or [],
                        },
                        "relationships": {"program": {"data": {"type": "program", "id": program_handle}}},
                    }
                }

                headers = await self._headers()
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{self.base_url}/hackers/reports",
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
                            f"Report submitted to {program_handle}",
                            data={
                                "report_id": data.get("data", {}).get("id"),
                                "url": data.get("data", {}).get("attributes", {}).get("url"),
                            },
                        )
                    return ExecutionResult(
                        False, "submit_report", "", error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                    )
            except Exception as e:
                return ExecutionResult(False, "submit_report", "", error=str(e))

    async def claim_bounty(self, report_id: str) -> ExecutionResult:
        """Claim bounty for a resolved report (HackerOne doesn't have direct bounty claim API)."""
        return ExecutionResult(
            False,
            "claim_bounty",
            "",
            error="HackerOne bounty claim is manual via platform. Use get_report to check status.",
        )

    async def get_report(self, report_id: str) -> ExecutionResult:
        """Get report details and status."""
        if not self.token:
            return ExecutionResult(False, "get_report", "", error="HACKERONE_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/hackers/reports/{report_id}",
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

    async def get_program(self, program_handle: str) -> ExecutionResult:
        """Get program details."""
        if not self.token:
            return ExecutionResult(False, "get_program", program_handle, error="HACKERONE_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/hackers/programs/{program_handle}",
                    headers=await self._headers(),
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_program", program_handle, data=data)
                return ExecutionResult(
                    False, "get_program", program_handle, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "get_program", program_handle, error=str(e))

    async def health_check(self) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "health_check", self.base_url, error="HACKERONE_API_KEY not configured")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/hackers/me", headers=await self._headers(), timeout=15)
                return ExecutionResult(resp.status_code == 200, "health_check", self.base_url)
            except Exception as e:
                return ExecutionResult(False, "health_check", self.base_url, error=str(e))
