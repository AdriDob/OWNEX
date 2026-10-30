"""Intigriti Executor — Submit reports, claim bounties on Intigriti."""

from __future__ import annotations

import os
from typing import Any

import httpx

from core.opportunity.executors import BaseExecutor, ExecutionResult


class IntigritiExecutor(BaseExecutor):
    """Executor for Intigriti — submit reports, claim bounties."""

    platform = "intigriti"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.client_id = self.config.get("client_id") or os.getenv("INTIGRITI_CLIENT_ID")
        self.client_secret = self.config.get("client_secret") or os.getenv("INTIGRITI_CLIENT_SECRET")
        self.base_url = self.config.get("base_url", "https://api.intigriti.com/external/researcher/v1")
        self._access_token: str | None = None

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
            return await self.claim_bounty(kwargs.get("submission_id") or "")
        if action == "get_submission":
            return await self.get_submission(kwargs.get("submission_id") or "")
        if action == "get_program":
            return await self.get_program(kwargs.get("program_id") or "")
        if action == "health_check":
            return await self.health_check()
        return ExecutionResult(False, action, "", error=f"Unknown action: {action}")

    async def _get_access_token(self) -> str | None:
        """Get OAuth2 access token."""
        if self._access_token:
            return self._access_token
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.intigriti.com/external/oauth2/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    self._access_token = resp.json().get("access_token")
                    return self._access_token
        except Exception:
            pass
        return None

    async def _headers(self) -> dict[str, str]:
        token = await self._get_access_token()
        return {
            "Authorization": f"Bearer {token}" if token else "",
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
        """Submit a vulnerability report to Intigriti."""
        if not self.client_id or not self.client_secret:
            return ExecutionResult(False, "submit_report", "", error="INTIGRITI_CLIENT_ID/SECRET not configured")

        if not program_id:
            return ExecutionResult(False, "submit_report", "", error="Program ID required")

        token = await self._get_access_token()
        if not token:
            return ExecutionResult(False, "submit_report", "", error="Failed to get access token")

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
                        f"{self.base_url}/submissions",
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
                            data={"submission_id": data.get("id"), "url": data.get("url")},
                        )
                    return ExecutionResult(
                        False, "submit_report", "", error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                    )
            except Exception as e:
                return ExecutionResult(False, "submit_report", "", error=str(e))

    async def claim_bounty(self, submission_id: str) -> ExecutionResult:
        if not self.client_id or not self.client_secret:
            return ExecutionResult(
                False, "claim_bounty", submission_id, error="INTIGRITI_CLIENT_ID/SECRET not configured"
            )

        token = await self._get_access_token()
        if not token:
            return ExecutionResult(False, "claim_bounty", submission_id, error="Failed to get access token")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/submissions/{submission_id}/claim",
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
        if not self.client_id or not self.client_secret:
            return ExecutionResult(False, "get_submission", "", error="INTIGRITI_CLIENT_ID/SECRET not configured")

        token = await self._get_access_token()
        if not token:
            return ExecutionResult(False, "get_submission", "", error="Failed to get access token")

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

    async def get_program(self, program_id: str) -> ExecutionResult:
        if not self.client_id or not self.client_secret:
            return ExecutionResult(False, "get_program", program_id, error="INTIGRITI_CLIENT_ID/SECRET not configured")

        token = await self._get_access_token()
        if not token:
            return ExecutionResult(False, "get_program", program_id, error="Failed to get access token")

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
        if not self.client_id or not self.client_secret:
            return ExecutionResult(
                False, "health_check", self.base_url, error="INTIGRITI_CLIENT_ID/SECRET not configured"
            )
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/health", timeout=15)
                return ExecutionResult(resp.status_code == 200, "health_check", self.base_url)
            except Exception as e:
                return ExecutionResult(False, "health_check", self.base_url, error=str(e))
