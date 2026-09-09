"""Code4rena Executor — Submit findings to Code4rena audit contests via GitHub.

Code4rena submissions are made via GitHub issues on the contest repository.
This executor prepares the submission package and creates the GitHub issue.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from core.opportunity.executors import BaseExecutor, ExecutionResult


class Code4renaExecutor(BaseExecutor):
    """Executor for Code4rena — submit findings to audit contests."""

    platform = "code4rena"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.token = self.config.get("token") or os.getenv("CODE4RENA_GITHUB_TOKEN")
        self.base_url = "https://api.github.com"

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        if action == "submit_finding":
            return await self.submit_finding(
                kwargs.get("contest_id") or "",
                kwargs.get("title") or "",
                kwargs.get("vulnerability_type") or "",
                kwargs.get("severity") or "",
                kwargs.get("description") or "",
                kwargs.get("impact") or "",
                kwargs.get("poc") or "",
                kwargs.get("recommended_mitigation") or "",
            )
        if action == "get_contest":
            return await self.get_contest(kwargs.get("contest_id") or "")
        if action == "get_findings":
            return await self.get_findings(kwargs.get("contest_id") or "")
        if action == "health_check":
            return await self.health_check()
        return ExecutionResult(False, action, "", error=f"Unknown action: {action}")

    async def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.v3+json",
        }

    async def submit_finding(
        self,
        contest_id: str,
        title: str,
        vulnerability_type: str,
        severity: str,
        description: str,
        impact: str = "",
        poc: str = "",
        recommended_mitigation: str = "",
    ) -> ExecutionResult:
        """Submit a finding as a GitHub issue to the Code4rena contest repo."""
        if not self.token:
            return ExecutionResult(False, "submit_finding", contest_id, error="CODE4RENA_GITHUB_TOKEN not configured")

        if not contest_id:
            return ExecutionResult(False, "submit_finding", "", error="Contest ID required")

        # Map severity to Code4rena labels
        severity_map = {
            "critical": "High",
            "high": "High",
            "medium": "Medium",
            "low": "QA (Quality Assurance)",
            "info": "Gas (Optimization)",
        }
        c4_severity = severity_map.get(severity.lower(), severity.capitalize())

        # Build issue body in Code4rena format
        body = f"""## Vulnerability Type
{vulnerability_type}

## Severity
{c4_severity}

## Description
{description}

## Impact
{impact}

## Proof of Concept
{poc}

## Recommended Mitigation
{recommended_mitigation}

---
*Submitted via OWNEX Code4rena Executor*"""

        issue_data = {
            "title": f"[{c4_severity}] {title}",
            "body": body,
            "labels": [c4_severity, "finding"],
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/repos/code-423n4/{contest_id}/issues",
                    headers=await self._headers(),
                    json=issue_data,
                    timeout=30,
                )

                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(
                        True,
                        "submit_finding",
                        contest_id,
                        f"Finding submitted to Code4rena contest {contest_id}",
                        data={"issue_number": data.get("number"), "url": data.get("html_url")},
                    )
                return ExecutionResult(
                    False, "submit_finding", contest_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
        except Exception as e:
            return ExecutionResult(False, "submit_finding", contest_id, error=str(e))

    async def get_contest(self, contest_id: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "get_contest", contest_id, error="CODE4RENA_GITHUB_TOKEN not configured")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.code4rena.com/api/contests/{contest_id}",
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_contest", contest_id, data=data)
                return ExecutionResult(
                    False, "get_contest", contest_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
        except Exception as e:
            return ExecutionResult(False, "get_contest", contest_id, error=str(e))

    async def get_findings(self, contest_id: str) -> ExecutionResult:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.code4rena.com/api/findings?contest={contest_id}",
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_findings", contest_id, data={"findings": data})
                return ExecutionResult(
                    False, "get_findings", contest_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
        except Exception as e:
            return ExecutionResult(False, "get_findings", contest_id, error=str(e))

    async def health_check(self) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "health_check", self.base_url, error="CODE4RENA_GITHUB_TOKEN not configured")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/user", headers=await self._headers(), timeout=15)
                return ExecutionResult(resp.status_code == 200, "health_check", self.base_url)
        except Exception as e:
            return ExecutionResult(False, "health_check", self.base_url, error=str(e))
