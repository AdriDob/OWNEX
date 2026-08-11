"""Algora Executor — Autonomous claim, fix, and submit for Algora.xyz OSS bounties."""

from __future__ import annotations

import base64
import os
from typing import Any

import httpx

from core.opportunity.executors import BaseExecutor, ExecutionResult


class AlgoraExecutor(BaseExecutor):
    """Executor for Algora.xyz — claim issues, create PRs, submit for review."""

    platform = "algora"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.token = self.config.get("token") or os.getenv("ALGORA_TOKEN")
        self.github_token = self.config.get("github_token") or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.algora.xyz/v1"
        self.github_base = "https://api.github.com"

    async def execute(self, action: str, **kwargs) -> ExecutionResult:
        if action == "claim_issue":
            return await self.claim_issue(kwargs.get("bounty_id"), kwargs.get("repo"), kwargs.get("issue_number"))
        if action == "create_pr":
            return await self.create_pr(
                kwargs.get("repo"),
                kwargs.get("branch"),
                kwargs.get("base"),
                kwargs.get("title"),
                kwargs.get("body"),
                kwargs.get("files"),
            )
        if action == "submit_pr":
            return await self.submit_pr(kwargs.get("bounty_id"), kwargs.get("pr_url"))
        if action == "get_bounty":
            return await self.get_bounty(kwargs.get("bounty_id"))
        return ExecutionResult(False, action, "", error=f"Unknown action: {action}")

    # === Algora API ===

    async def claim_issue(self, bounty_id: str, repo: str, issue_number: int) -> ExecutionResult:
        """Claim a bounty issue on Algora."""
        if not self.token:
            return ExecutionResult(False, "claim_issue", bounty_id, error="ALGORA_TOKEN not configured")

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
                        False, "claim_issue", bounty_id, error=f"Algora API {resp.status_code}: {resp.text}"
                    )
        except Exception as e:
            return ExecutionResult(False, "claim_issue", bounty_id, error=str(e))

    async def submit_pr(self, bounty_id: str, pr_url: str) -> ExecutionResult:
        """Submit a PR for review on Algora."""
        if not self.token:
            return ExecutionResult(False, "submit_pr", bounty_id, error="ALGORA_TOKEN not configured")

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
                        False, "submit_pr", bounty_id, error=f"Algora API {resp.status_code}: {resp.text}"
                    )
        except Exception as e:
            return ExecutionResult(False, "submit_pr", bounty_id, error=str(e))

    async def get_bounty(self, bounty_id: str) -> ExecutionResult:
        """Get bounty details."""
        if not self.token:
            return ExecutionResult(False, "get_bounty", bounty_id, error="ALGORA_TOKEN not configured")

        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/bounties/{bounty_id}", headers=headers, timeout=15)
                if resp.status_code == 200:
                    return ExecutionResult(True, "get_bounty", bounty_id, "Bounty fetched", data=resp.json())
                return ExecutionResult(False, "get_bounty", bounty_id, error=f"API {resp.status_code}: {resp.text}")
        except Exception as e:
            return ExecutionResult(False, "get_bounty", bounty_id, error=str(e))

    # === GitHub API (for PR creation) ===

    async def create_pr(
        self,
        repo: str,
        branch: str,
        base: str,
        title: str,
        body: str,
        files: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Create a PR on GitHub with optional file changes."""
        if not self.github_token:
            return ExecutionResult(False, "create_pr", repo, error="GITHUB_TOKEN not configured")

        headers = {"Authorization": f"Bearer {self.github_token}", "Accept": "application/vnd.github+json"}

        try:
            async with httpx.AsyncClient() as client:
                # 1. Get base branch SHA
                ref_resp = await client.get(f"{self.github_base}/repos/{repo}/git/ref/heads/{base}", headers=headers)
                if ref_resp.status_code != 200:
                    return ExecutionResult(False, "create_pr", repo, error=f"Base ref not found: {ref_resp.text}")
                ref_data = ref_resp.json()
                base_sha = ref_data.get("object", {}).get("sha")
                if not base_sha:
                    return ExecutionResult(False, "create_pr", repo, error=f"Base ref not found or invalid: {ref_data}")

                # 2. Create new branch
                branch_resp = await client.post(
                    f"{self.github_base}/repos/{repo}/git/refs",
                    headers=headers,
                    json={"ref": f"refs/heads/{branch}", "sha": base_sha},
                )
                if branch_resp.status_code not in (200, 201):
                    # Branch might exist, try to get it
                    branch_resp = await client.get(
                        f"{self.github_base}/repos/{repo}/git/ref/heads/{branch}", headers=headers
                    )
                    if branch_resp.status_code != 200:
                        return ExecutionResult(
                            False, "create_pr", repo, error=f"Branch creation failed: {branch_resp.text}"
                        )

                # 3. If files provided, commit them
                if files:
                    await self._commit_files(client, headers, repo, branch, base_sha, files, title)

                # 4. Create PR
                pr_resp = await client.post(
                    f"{self.github_base}/repos/{repo}/pulls",
                    headers=headers,
                    json={"title": title, "head": branch, "base": base, "body": body, "maintainer_can_modify": True},
                )

                if pr_resp.status_code in (200, 201):
                    pr_data = pr_resp.json()
                    return ExecutionResult(
                        True,
                        "create_pr",
                        repo,
                        f"Created PR #{pr_data['number']}: {title}",
                        data={"pr_number": pr_data["number"], "pr_url": pr_data["html_url"], "branch": branch},
                    )
                else:
                    return ExecutionResult(False, "create_pr", repo, error=f"PR creation failed: {pr_resp.text}")

        except Exception as e:
            return ExecutionResult(False, "create_pr", repo, error=str(e))

    async def _commit_files(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        repo: str,
        branch: str,
        base_sha: str,
        files: dict[str, str],
        commit_message: str,
    ) -> str:
        """Commit multiple files to a branch. Returns new tree SHA."""
        # Create blobs for each file
        blob_shas = {}
        for path, content in files.items():
            blob_resp = await client.post(
                f"{self.github_base}/repos/{repo}/git/blobs",
                headers=headers,
                json={"content": base64.b64encode(content.encode()).decode(), "encoding": "base64"},
            )
            if blob_resp.status_code not in (200, 201):
                raise Exception(f"Blob creation failed for {path}: {blob_resp.text}")
            blob_shas[path] = blob_resp.json()["sha"]

        # Get base tree
        tree_resp = await client.get(f"{self.github_base}/repos/{repo}/git/trees/{base_sha}", headers=headers)
        if tree_resp.status_code != 200:
            raise Exception(f"Base tree fetch failed: {tree_resp.text}")
        base_tree = tree_resp.json()["sha"]

        # Create new tree with files
        tree_items = [{"path": path, "mode": "100644", "type": "blob", "sha": sha} for path, sha in blob_shas.items()]
        new_tree_resp = await client.post(
            f"{self.github_base}/repos/{repo}/git/trees",
            headers=headers,
            json={"base_tree": base_tree, "tree": tree_items},
        )
        if new_tree_resp.status_code not in (200, 201):
            raise Exception(f"Tree creation failed: {new_tree_resp.text}")
        new_tree_sha = new_tree_resp.json()["sha"]

        # Create commit
        commit_resp = await client.post(
            f"{self.github_base}/repos/{repo}/git/commits",
            headers=headers,
            json={"message": commit_message, "tree": new_tree_sha, "parents": [base_sha]},
        )
        if commit_resp.status_code not in (200, 201):
            raise Exception(f"Commit creation failed: {commit_resp.text}")
        commit_sha = commit_resp.json()["sha"]

        # Update branch ref
        ref_resp = await client.patch(
            f"{self.github_base}/repos/{repo}/git/refs/heads/{branch}",
            headers=headers,
            json={"sha": commit_sha, "force": True},
        )
        if ref_resp.status_code not in (200, 201):
            raise Exception(f"Branch update failed: {ref_resp.text}")

        return commit_sha
