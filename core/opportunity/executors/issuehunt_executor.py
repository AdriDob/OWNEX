"""IssueHunt Executor — Claim and submit PR work on IssueHunt.io."""

from __future__ import annotations

import os
from typing import Any

import httpx

from core.opportunity.executors import BaseExecutor, ExecutionResult


class IssueHuntExecutor(BaseExecutor):
    """Executor for IssueHunt.io — claim issues, create PRs, submit for review."""

    platform = "issuehunt"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.token = self.config.get("token") or os.getenv("ISSUEHUNT_TOKEN")
        self.github_token = self.config.get("github_token") or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://issuehunt.io/api/v1"
        self.github_base = "https://api.github.com"

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        """Execute an action for IssueHunt."""
        if action == "claim_issue":
            return await self.claim_issue(
                kwargs.get("bounty_id"),
                kwargs.get("repo"),
                kwargs.get("issue_number"),
            )
        if action == "submit_pr":
            return await self.submit_pr(kwargs.get("bounty_id"), kwargs.get("pr_url"))
        if action == "get_bounty":
            return await self.get_bounty(kwargs.get("bounty_id"))
        return ExecutionResult(False, action, "", error=f"Unknown action: {action}")

    async def claim_issue(self, bounty_id: str, repo: str, issue_number: int) -> ExecutionResult:
        """Claim a bounty issue on IssueHunt."""
        if not self.token:
            return ExecutionResult(False, "claim_issue", bounty_id, error="ISSUEHUNT_TOKEN not configured")

        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/bounties/{bounty_id}/claim",
                    headers=headers,
                    json={"repository": repo, "issue_number": issue_number},
                    timeout=30,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(
                        True,
                        "claim_issue",
                        bounty_id,
                        f"Claimed bounty {bounty_id} on {repo}#{issue_number}",
                        data={"claim_id": data.get("claim_id"), "expires_at": data.get("expires_at")},
                    )
                else:
                    return ExecutionResult(
                        False, "claim_issue", bounty_id, error=f"IssueHunt API {resp.status_code}: {resp.text}"
                    )
        except Exception as e:
            return ExecutionResult(False, "claim_issue", bounty_id, error=str(e))

    async def submit_pr(self, bounty_id: str, pr_url: str) -> ExecutionResult:
        """Submit a PR for review on IssueHunt."""
        if not self.token:
            return ExecutionResult(False, "submit_pr", bounty_id, error="ISSUEHUNT_TOKEN not configured")

        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/bounties/{bounty_id}/submit",
                    headers=headers,
                    json={"pull_request_url": pr_url},
                    timeout=30,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(
                        True,
                        "submit_pr",
                        bounty_id,
                        f"Submitted PR {pr_url} for bounty {bounty_id}",
                        data={"submission_id": data.get("submission_id"), "status": data.get("status")},
                    )
                else:
                    return ExecutionResult(
                        False, "submit_pr", bounty_id, error=f"IssueHunt API {resp.status_code}: {resp.text}"
                    )
        except Exception as e:
            return ExecutionResult(False, "submit_pr", bounty_id, error=str(e))

    async def get_bounty(self, bounty_id: str) -> ExecutionResult:
        """Get bounty details."""
        if not self.token:
            return ExecutionResult(False, "get_bounty", bounty_id, error="ISSUEHUNT_TOKEN not configured")

        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/bounties/{bounty_id}", headers=headers, timeout=15)
                if resp.status_code == 200:
                    return ExecutionResult(True, "get_bounty", bounty_id, "Bounty fetched", data=resp.json())
                return ExecutionResult(False, "get_bounty", bounty_id, error=f"API {resp.status_code}: {resp.text}")
        except Exception as e:
            return ExecutionResult(False, "get_bounty", bounty_id, error=str(e))
