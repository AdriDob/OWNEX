"""YesWeHack Executor — Submit reports, claim bounties on YesWeHack."""

from __future__ import annotations

import os
from typing import Any

import httpx

from core.opportunity.executors import BaseExecutor, ExecutionResult


class YesWeHackExecutor(BaseExecutor):
    """Executor for YesWeHack — submit reports, claim bounties."""

    platform = "yeswehack"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.token = self.config.get("token") or os.getenv("YESWEHACK_API_KEY")
        self.base_url = self.config.get("base_url", "https://api.yeswehack.com")

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        if action == "submit_report":
            return await self.submit_report(
                kwargs.get("program_slug") or "",
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
            return await self.claim_bounty(kwargs.get("submission_id") or "")
        if action == "get_submission":
            return await self.get_submission(kwargs.get("submission_id") or "")
        if action == "get_program":
            return await self.get_program(kwargs.get("program_slug") or "")
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
        program_slug: str,
        title: str,
        vulnerability_type: str,
        severity: str,
        description: str,
        impact: str = "",
        steps_to_reproduce: str = "",
        poc: str = "",
        attachments: list[str] | None = None,
    ) -> ExecutionResult:
        """Submit a vulnerability report to YesWeHack."""
        if not self.token:
            return ExecutionResult(False, "submit_report", "", error="YESWEHACK_API_KEY not configured")

        if not program_slug:
            return ExecutionResult(False, "submit_report", "", error="Program slug required")

        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "report": {
                        "title": title,
                        "vulnerability_type": vulnerability_type,
                        "severity": severity,
                        "description": description,
                        "impact": impact,
                        "steps_to_reproduce": steps_to_reproduce,
                        "poc": poc,
                        "attachments": attachments or [],
                    }
                }

                headers = await self._headers()
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{self.base_url}/programs/{program_slug}/reports",
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
                            f"Report submitted to {program_slug}",
                            data={"report_id": data.get("id"), "url": data.get("url")},
                        )
                    return ExecutionResult(
                        False, "submit_report", "", error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                    )
            except Exception as e:
                return ExecutionResult(False, "submit_report", "", error=str(e))

    async def claim_bounty(self, submission_id: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "claim_bounty", submission_id, error="YESWEHACK_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/submissions/{submission_id}/claim_bounty",
                    headers=await self._headers(),
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(True, "claim_bounty", submission_id, data={"response": data})
                return ExecutionResult(
                    False, "claim_bounty", submission_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "claim_bounty", submission_id, error=str(e))

    async def get_submission(self, submission_id: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "get_submission", "", error="YESWEHACK_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/submissions/{submission_id}",
                    headers=await self._headers(),
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_submission", submission_id, data={"submission": data})
                return ExecutionResult(
                    False, "get_submission", submission_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "get_submission", "", error=str(e))

    async def get_program(self, program_slug: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "get_program", program_slug, error="YESWEHACK_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/programs/{program_slug}",
                    headers=await self._headers(),
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_program", program_slug, data=data)
                return ExecutionResult(
                    False, "get_program", program_slug, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "get_program", program_slug, error=str(e))

    async def health_check(self) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "health_check", self.base_url, error="YESWEHACK_API_KEY not configured")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/health", timeout=15)
                return ExecutionResult(resp.status_code == 200, "health_check", self.base_url)
            except Exception as e:
                return ExecutionResult(False, "health_check", self.base_url, error=str(e))
